import asyncio
import time

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

from game.game_logic.player import Player
from game.models import Question


class Game:
    QUESTION_LENGTH = 10
    MAX_SCORE = 1000
    MIN_SCORE = 100

    def __init__(self, game_code, channel_layer, on_game_end):
        self.game_code = game_code
        self.channel_layer = channel_layer
        self.on_game_end = on_game_end
        self.players = {}
        self.running_game_task = None
        self.current_question = None

# Private:

    def _is_username_available(self, username):
        return False if username in self.players.values() else True

    def _get_available_username(self, username):
        if not self._is_username_available(username):
            index = 1
            while not self._is_username_available(username + f" #{index}"):
                index += 1
            username = username + f" #{index}"
        return username

    def _get_all_scores(self):
        return [{'user': p.username, 'score': p.total_score()} for p in self.players.values()]

    def _get_all_usernames(self):
        return [p.username for p in self.players.values()]

    async def _send_list_of_users(self):
        await self.channel_layer.group_send(
            self.game_code,
            {
                "type": "show_users",
                "users": self._get_all_usernames(),
            },
        )

    async def _send_error(self, channel_name, msg):
        await self.channel_layer.send(
            channel_name,
            {
                "type": "error",
                "msg": msg,
            },
        )

    async def _ask_question(self, game_code, question, question_id):
        self.current_question = {'id': question_id, 'correct_answer': question.correct_answer,
                                            'length': self.QUESTION_LENGTH, 'start_time': time.time()}
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'ask_question',
                'question_id': question_id,
                'time': self.QUESTION_LENGTH,
                'question': question.content,
                'answers': question.answers
            }
        )

        await asyncio.sleep(self.QUESTION_LENGTH)
        self.current_question = None
        for player_channel in self.players:
            await self.channel_layer.send(
                player_channel,
                {
                    'type': 'question_end',
                    'question_id': question_id,
                    'correct_answer': self.players[player_channel].is_answer_correct(question_id),
                }
            )

    async def _get_random_questions(self, amount):
        questions = await database_sync_to_async(Question.objects.all().order_by)('?')
        random_questions = await sync_to_async(list)(questions[:amount])
        return random_questions

    async def _run_game(self):
        await self.channel_layer.group_send(
            self.game_code,
            {
                'type': 'game_started',
            }
        )

        questions = await self._get_random_questions(3)

        for i, q in enumerate(questions):
            await self._ask_question(self.game_code, q, i)
            await asyncio.sleep(5)

        await self.channel_layer.group_send(
            self.game_code,
            {
                'type': 'game_ended',
                'scores': self._get_all_scores()
            }
        )
        await self.on_game_end(self.game_code)

# Public:

    async def remove_player(self, channel_name):
        self.players.pop(channel_name)
        await self.channel_layer.group_discard(self.game_code, channel_name)

        if len(self.players) == 0:
            if self.running_game_task:
                self.running_game_task.cancel()
            await self.on_game_end(self.game_code)
            return

        # Send updated list of users attending the game
        await self._send_list_of_users()

    async def add_player(self, channel_name, username):
        if self.running_game_task:
            await self._send_error(channel_name, 'Game is running already')
            return
        new_username = self._get_available_username(username)
        self.players[channel_name] = Player(channel_name, username)
        await self.channel_layer.send(
            channel_name,
            {
                "type": "join_successful",
                "username": new_username,
            },
        )
        await self.channel_layer.group_add(self.game_code, channel_name)
        await self._send_list_of_users()
        return new_username

    async def submit_answer(self, channel_name, question_id, answer):
        if not self.current_question:
            await self._send_error(channel_name, "There is no active question")
            return
        if question_id != self.current_question['id']:
            await self._send_error(channel_name, "Wrong question id")
            return
        answer_time = time.time() - self.current_question['start_time']
        if answer_time > self.current_question['length']:
            await self._send_error(channel_name, "There is no active question")
        # Calculate score
        score = 0
        if self.current_question['correct_answer'] == answer:
            score = int((1 - answer_time/self.current_question['length']) *
                        (self.MAX_SCORE-self.MIN_SCORE) + self.MIN_SCORE)
        # Save answer
        self.players[channel_name].set_answer(question_id, score)

    async def start_game(self, channel_name):
        if not self.running_game_task:
            self.running_game_task = asyncio.create_task(self._run_game())
        else:
            await self._send_error(channel_name, "Game is running already")
