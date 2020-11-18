import random

from channels.consumer import AsyncConsumer
from game.game_logic.game import Game


""" GameWorker - manages all active games """


class GameWorker(AsyncConsumer):
    QUESTION_LENGTH = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_games = {}
        self.current_players = {}  # {'player_channel_name': 'game_code', ...}
        print('GameWorker started.')

# Private:

    def _get_new_game_code(self):
        while True:
            code = random.randint(0, 99)
            if not self.active_games.get(code, None):
                return str(code)

    async def _remove_player_from_game(self, channel_name):
        game_code = self.current_players[channel_name]
        await self.active_games[game_code].remove_player(channel_name)
        del self.current_players[channel_name]

    async def _add_player_to_game(self, channel_name, username, game_code):
        if await self.active_games[game_code].add_player(channel_name, username):
            self.current_players[channel_name] = game_code

    async def _remove_game(self, game_code):
        print(f"Removing game {game_code}")
        players = self.active_games[game_code].players
        for p in players:
            await self.channel_layer.group_discard(game_code, p)
            del self.current_players[p]
        self.active_games.pop(game_code)

    async def _send_error(self, channel_name, msg):
        await self.channel_layer.send(
            channel_name,
            {
                "type": "error",
                "msg": msg,
            },
        )

# Public (available via channel layer):

    async def create_game(self, event):
        channel_name = event['channel_name']
        username = event['username']
        game_code = self._get_new_game_code()

        # Data validation
        if not username:
            await self._send_error(channel_name, "Some data is missing!")
            return
        # Drop player from a game if is playing already
        if channel_name in self.current_players:
            await self._remove_player_from_game(channel_name)

        # Create game
        self.active_games[game_code] = Game(game_code, self.channel_layer, self._remove_game)
        await self.channel_layer.send(
            channel_name,
            {
                "type": "game_created",
                "game_code": game_code,
            },
        )
        # Add player to the game
        await self._add_player_to_game(channel_name, username, game_code)

    async def add_user(self, event):
        channel_name = event['channel_name']
        username = event['username']
        game_code = event['game_code']

        # Data validation
        if not username or game_code is None:
            await self._send_error(channel_name, "Some data is missing")
            return
        if channel_name in self.current_players:
            if self.current_players[channel_name] == game_code:
                await self._send_error(channel_name, 'You are in this game already')
                return
            await self._remove_player_from_game(channel_name)
        if game_code not in self.active_games:  # If game does not exist
            await self._send_error(channel_name, f"Game with code {game_code} does not exist")
            return

        # Add player to the game
        await self._add_player_to_game(channel_name, username, game_code)

    async def remove_user(self, event):
        channel_name = event['channel_name']

        # Data validation
        if channel_name not in self.current_players:
            await self._send_error(channel_name, "You are not in a game")
            return

        # Remove player from a game
        await self._remove_player_from_game(channel_name)

    async def submit_answer(self, event):
        channel_name = event['channel_name']

        # Data validation
        if channel_name not in self.current_players:
            await self._send_error(channel_name, "You are not in a game")
            return
        # TODO: Better error messages
        try:
            question_id = int(event['question_id'])
        except Exception as e:
            await self._send_error(channel_name, "Question id is not a number")
            return
        try:
            answer = int(event['answer'])
        except Exception as e:
            await self._send_error(channel_name, "Wrong answer format")
            return

        # Submit answer
        game_code = self.current_players[channel_name]
        await self.active_games[game_code].submit_answer(channel_name, question_id, answer)

    async def start_game(self, event):
        channel_name = event['channel_name']

        # Data validation
        if channel_name not in self.current_players:
            await self._send_error(channel_name, "You are not in a game")
            return

        # Start game
        game_code = self.current_players[channel_name]
        await self.active_games[game_code].start_game(channel_name)
