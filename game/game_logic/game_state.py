import time

from game.game_logic.player import Player


class GameState:
    MAX_SCORE = 1000
    MIN_SCORE = 100

    def __init__(self, code):
        self.code = code
        self.players = {}
        self.running = False
        self.current_question = None

# Private:

    def _is_username_available(self, username):
        return False if username in self.players.values() else True

    def _get_user(self, channel_name):
        return self.players.get(channel_name, None)

# Public:

    def start_game(self):
        if self.running:
            return False
        self.running = True
        return True

    def is_game_running(self):
        return self.running

    def get_available_username(self, username):
        if not self._is_username_available(username):
            index = 1
            while not self._is_username_available(username + f" #{index}"):
                index += 1
            username = username + f" #{index}"
        return username

    def add_user(self, channel_name, username):
        username = self.get_available_username(username)
        self.players[channel_name] = Player(channel_name, username)
        return username

    def remove_user(self, channel_name):
        self.players.pop(channel_name)

    def set_answer(self, channel_name, question_id, answer):
        if not self.current_question or question_id != self.current_question['id']:
            return False
        answer_time = time.time() - self.current_question['start_time']
        if answer_time > self.current_question['length']:
            return False
        # Calculate score
        score = 0
        if self.current_question['correct_answer'] == answer:
            score = int((1 - answer_time/self.current_question['length']) * (self.MAX_SCORE-self.MIN_SCORE)
                        + self.MIN_SCORE)
        # Save answer
        self.players[channel_name].set_answer(question_id, score)
        return True

    def check_if_user_was_right(self, channel_name, question_id):
        return self.players[channel_name].is_correct_answer(question_id)

    def get_all_scores(self):
        return [{'user': p.username, 'score': p.total_score()} for p in self.players.values()]

    def get_list_of_usernames(self):
        return [p.username for p in self.players.values()]

    def get_list_of_users_channels(self):
        return self.players
