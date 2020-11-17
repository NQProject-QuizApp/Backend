import asyncio
import json
import random
import time

from asgiref.sync import sync_to_async
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.db import database_sync_to_async

from game.game_logic.game_state import GameState
from game.models import Question
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer

""" GameWorker - manages all active games """


class Game:
    QUESTION_LENGTH = 10

    def __init__(self, game_code, channel_layer, on_game_end):
        self.game_code = game_code
        self.game_state = GameState(game_code)
        self.channel_layer = channel_layer
        self.on_game_end = on_game_end

# Private:

    async def _send_list_of_users(self):
        users = self.game_state.get_list_of_usernames()
        await self.channel_layer.group_send(
            self.game_code,
            {
                "type": "show_users",
                "users": users,
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
        self.game_state.current_question = {'id': question_id, 'correct_answer': question.correct_answer,
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
        self.game_state.current_question = None
        players = self.game_state.get_list_of_users_channels()
        for player_channel in players:
            await self.channel_layer.send(
                player_channel,
                {
                    'type': 'question_end',
                    'question_id': question_id,
                    'correct_answer': self.game_state.check_if_user_was_right(
                        player_channel, question_id),
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
                'scores': self.game_state.get_all_scores()
            }
        )
        await self.on_game_end(self.game_code)
        # await self._remove_game(game_code) TODO: call it in game_manager

# Public:

    async def remove_player(self, channel_name):
        self.game_state.players.pop(channel_name)
        await self.channel_layer.group_discard(self.game_code, channel_name)
        # del self.current_players[channel_name]  TODO: call it in game_manager

        if len(self.game_state.players) == 0 and not self.game_state.running:
            await self.on_game_end(self.game_code)
            return

        # Send updated list of users attending the game
        await self._send_list_of_users()

    async def add_player(self, channel_name, username):
        if self.game_state.running:
            return  # TODO: Error message
        new_username = self.game_state.add_user(channel_name, username)
        await self.channel_layer.send(
            channel_name,
            {
                "type": "join_successful",
                "username": new_username,
            },
        )
        await self._send_list_of_users()
        # self.current_players[channel_name] = game_code  TODO: call it in game_manager
        await self.channel_layer.group_add(self.game_code, channel_name)
        return new_username

    async def submit_answer(self, channel_name, question_id, answer):
        if not self.game_state.set_answer(channel_name, question_id, answer):
            await self._send_error(channel_name, "Error when submitting answer")  # TODO: better error message

    async def start_game(self, channel_name):
        if not self.game_state.running:
            self.game_state.running = True
            asyncio.create_task(self._run_game())
        else:
            await self._send_error(channel_name, "Game is running already")
