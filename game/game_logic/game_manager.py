import asyncio
import json
import random

from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer


""" GameWorker - manages all active games """


class GameWorker(AsyncConsumer):
    QUESTION_LENGTH = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_games = {}
        self.current_question = None
        print('GameWorker started.')

    def get_new_game_code(self):
        while True:
            code = random.randint(0, 999999)
            if not self.active_games.get(code, None):
                return str(code)

    async def create_game(self, event):
        print('Creating game')
        game_code = self.get_new_game_code()
        username = event['username']
        channel_name = event['channel_name']
        self.active_games[game_code] = GameState(game_code)
        self.active_games[game_code].add_user(username)
        await self.channel_layer.group_add(
            game_code,
            channel_name
        )
        await self.channel_layer.send(
            channel_name,
            {
                "type": "game_created",
                "game_code": game_code,
            },
        )

    def remove_game(self, game_code):
        self.active_games.pop(game_code)

    async def add_user(self, event):
        game_code = event['game_code']
        channel_name = event['channel_name']
        username = event['username']
        self.active_games[game_code].add_user(username)
        users = self.active_games[game_code].get_users()
        await self.channel_layer.group_add(
            game_code,
            channel_name
        )
        await self.channel_layer.group_send(
            game_code,
            {
                "type": "show_users",
                "users": users,
            },
        )

    async def submit_answer(self, event):
        username = event['username']
        game_code = event['game_code']
        answer = int(event['answer'])
        question_id = int(event['question_id'])
        if question_id == self.current_question['id']:
            score = 0
            if answer == self.current_question['correct_answer']:
                score = 10
            if self.active_games[game_code].set_answer(username, question_id, score):  # If first try, send result
                await self.channel_layer.group_send(
                    game_code,
                    {
                        'type': 'question_end',
                        'question_id': self.current_question['id'],
                        'correct_answer': True if score > 0 else False,
                    }
                )

    async def start_game(self, event):
        game_code = event['game_code']
        if self.active_games[game_code].start_game():
            asyncio.create_task(self.run_game(game_code))

    async def ask_question(self, game_code, question_id):
        self.current_question = {
            'id': question_id,
            'time': self.QUESTION_LENGTH,
            'content': 'What year is now?',
            'answers': ['2020', '2024', '2019', '2018'],
            'correct_answer': 0
        }
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'ask_question',
                'question_id': self.current_question['id'],
                'time': self.current_question['time'],
                'question': self.current_question['content'],
                'answers': self.current_question['answers']
            }
        )
        await asyncio.sleep(self.current_question['time'])

    async def run_game(self, game_code):
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'game_started',
            }
        )

        for q in range(3):
            await asyncio.sleep(2)
            await self.ask_question(game_code, q)

        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'game_ended',
                'scores': f"{self.active_games[game_code].get_all_scores()}"
            }
        )
        self.remove_game(game_code)


class GameState:
    def __init__(self, code):
        self.code = code
        self.users = []
        self.running = False

    def start_game(self):
        if self.running:
            return False
        self.running = True
        return True

    def add_user(self, username):
        self.users.append({"user": username, "answers": []})

    def get_user(self, username):
        for u in self.users:
            if u["user"] == username:
                return u
        raise AttributeError

    def count_user_score(self, user):
        score = 0
        for q in user['answers']:
            score += q['score']
        return score

    def set_answer(self, username, question_id, score):
        user = self.get_user(username)
        for q in user['answers']:
            if q['question_id'] == question_id:
                return False
        user['answers'].append({"question_id": question_id, "score": score})
        return True

    def check_if_user_was_right(self, username, question_id):
        user = self.get_user(username)
        for q in user['answers']:
            if q['question_id'] == question_id:
                if q['score'] > 0:
                    return True
                return False
        return False

    def get_all_scores(self):
        return [{'user': u['user'], 'score': self.count_user_score(u)} for u in self.users]

    def get_users(self):
        return [u["user"] for u in self.users]
