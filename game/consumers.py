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
            game_code = text_data_json['game_code']
            answer = text_data_json['answer']
            question_id = text_data_json["question_id"]
            await self.channel_layer.send(
                "game-manager",
                {
                    "type": "submit_answer",
                    "channel_name": self.channel_name,
                    "game_code": game_code,
                    "question_id": question_id,
                    "answer": answer,
                },
            )
            pass

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
        await self.leave_group()

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_end',
            'scores': event['scores'],
        }))
        await self.leave_group()

    async def send(self, text_data=None, bytes_data=None, close=False):
        print('Sent: ' + text_data)
        await super().send(text_data, bytes_data, close)
