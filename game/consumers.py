import asyncio
import json
import random

from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def _leave_group(self):
        await self.channel_layer.send(
            "game-manager",
            {
                "type": "remove_user",
                "channel_name": self.channel_name,
            })

    async def disconnect(self, close_code):
        await self._leave_group()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        text_data_json = json.loads(text_data)
        request_type = text_data_json.get('type', None)
        if not request_type:
            return

        print('Received: ' + str(text_data_json))
        if request_type == 'new_game':
            username = text_data_json.get('user', None)
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "create_game",
                    "channel_name": self.channel_name,
                    "username": username,
                },
            )
        elif request_type == 'join':
            username = text_data_json.get('user', None)
            game_code = text_data_json.get('game_code', None)
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "add_user",
                    "game_code": game_code,
                    "channel_name": self.channel_name,
                    "username": username,
                },
            )
        elif request_type == 'start':
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "start_game",
                    "channel_name": self.channel_name,
                },
            )
        elif request_type == 'answer':
            answer = text_data_json.get('answer', None)
            question_id = text_data_json.get('question_id', None)
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "submit_answer",
                    "channel_name": self.channel_name,
                    "question_id": question_id,
                    "answer": answer,
                },
            )
        elif request_type == 'leave':
            await self._leave_group()

    async def game_created(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_created',
            'code': event['game_code']
        }))

    async def join_successful(self, event):
        await self.send(text_data=json.dumps({
            'type': 'join_successful',
            'username': event['username']
        }))

    async def error(self, event):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'msg': event['msg']
        }))

    async def game_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_started',
        }))

    async def ask_question(self, event):
        await self.send(text_data=json.dumps({
            'type': 'question',
            'question_id': event['question_id'],
            'time': event['time'],
            'question': event['question'],
            'answers': event['answers'],
        }))

    async def show_users(self, event):
        await self.send(text_data=json.dumps({
            'type': 'users_list',
            'users': event['users']
        }))

    async def question_end(self, event):
        await self.send(text_data=json.dumps({
            'type': 'question_end',
            'question_id': event['question_id'],
            'correct_answer': event['correct_answer'],
        }))

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_end',
            'scores': event['scores'],
        }))

    async def send(self, text_data=None, bytes_data=None, close=False):
        print('Sent: ' + text_data)
        await super().send(text_data, bytes_data, close)
