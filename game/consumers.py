import asyncio
import json
import random

from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = None
        await self.accept()

    async def leave_group(self):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def disconnect(self, close_code):
        await self.leave_group()

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        request = text_data_json['type']

        print('Received: ' + str(text_data_json))
        if request == 'new_game':
            username = text_data_json['user']
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "create_game",
                    "channel_name": self.channel_name,
                    "username": username,
                },
            )
        elif request == 'join':
            username = text_data_json['user']
            game_code = text_data_json['game_code']
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "add_user",
                    "game_code": game_code,
                    "channel_name": self.channel_name,
                    "username": username,
                },
            )
        elif request == 'start':
            game_code = text_data_json['game_code']
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "start_game",
                    "game_code": game_code,
                },
            )
        elif request == 'answer':
            username = text_data_json['user']
            game_code = text_data_json['game_code']
            answer = text_data_json['answer']
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "submit_answer",
                    "username": username,
                    "game_code": game_code,
                    "answer": answer,
                },
            )
            pass

    async def game_created(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_created',
            'code': f"{event['game_code']}"
        }))

    async def game_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_started',
        }))

    async def ask_question(self, event):
        await self.send(text_data=json.dumps({
            'type': 'question',
            'question': f"{event['question']}",
            'answers': f"{event['answers']}",
        }))

    async def show_users(self, event):
        await self.send(text_data=json.dumps({
            'type': 'users_list',
            'users': f"{event['users']}"
        }))

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_end',
            'scores': f"{event['scores']}",
        }))
        await self.leave_group()

    async def send(self, text_data=None, bytes_data=None, close=False):
        print('Sent: ' + text_data)
        await super().send(text_data, bytes_data, close)


""" GameWorker - manages all active games """


class PrintConsumer(AsyncWebsocketConsumer):
    async def test_print(self, message):
        print("Test: " + message["text"])


class LogFileConsumer(SyncConsumer):
    def read_file(self, message):
        print(message)


class GameWorker(AsyncConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_games = {}
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
        answer = event['answer']
        if answer == '1':
            self.active_games[game_code].add_score(username, 10)

    async def start_game(self, event):
        game_code = event['game_code']
        asyncio.create_task(self.run_game(game_code))

    async def run_game(self, game_code):
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'game_started',
            }
        )
        await asyncio.sleep(2)
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'ask_question',
                'question': 'What year is now?',
                'answers': ['2020', '2024', '2019', '2018']
            }
        )
        await asyncio.sleep(10)
        await self.channel_layer.group_send(
            game_code,
            {
                'type': 'game_ended',
                'scores': f"{self.active_games[game_code].get_scores()}"
            }
        )
        self.remove_game(game_code)


class GameState:
    def __init__(self, code):
        self.code = code
        self.users = []
        self.running = False

    def add_user(self, username):
        self.users.append({"user": username, "score": 0})

    def add_score(self, username, score):
        for u in self.users:
            if u["user"] == username:
                u["score"] += score
                return
        raise AttributeError

    def get_scores(self):
        return self.users

    def get_users(self):
        return [u["user"] for u in self.users]
