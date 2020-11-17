import time


class GameState:
    MAX_SCORE = 1000

    def __init__(self, code):
        self.code = code
        self.users = []
        self.running = False
        self.current_question = None

# Private:

    def _is_username_available(self, username):
        for u in self.users:
            if u["username"] == username:
                return False
        return True

    def _get_user(self, channel_name):
        for u in self.users:
            if u["channel_name"] == channel_name:
                return u
        return None

    def _count_user_score(self, user):
        score = 0
        for q in user['answers']:
            score += q['score']
        return score

# Public:

    def start_game(self):
        if self.running:
            return False
        self.running = True
        return True

    def is_game_running(self):
        return self.running

    def add_user(self, channel_name, username):
        if not self._is_username_available(username):
            index = 2
            while not self._is_username_available(username + f" #{index}"):
                index += 1
            username = username + f" #{index}"
        self.users.append({"channel_name": channel_name, 'username': username, "answers": []})
        return username

    def remove_user(self, channel_name):
        self.users.remove(self._get_user(channel_name))
        return

    def set_answer(self, channel_name, question_id, answer):
        if not self.current_question or question_id != self.current_question['id']:
            return False
        answer_time = time.time() - self.current_question['start_time']
        question_length = self.current_question['length']
        if answer_time > question_length:
            return False
        # Calculate score
        score = 0
        if self.current_question['correct_answer'] == answer:
            score = int((1 - answer_time/question_length) * self.MAX_SCORE)
        # Save answer
        user = self._get_user(channel_name)
        for q in user['answers']:
            if q['question_id'] == question_id:
                return False  # Return if already answered
        user['answers'].append({"question_id": question_id, "score": score})
        return True

    def check_if_user_was_right(self, channel_name, question_id):
        user = self._get_user(channel_name)
        for q in user['answers']:
            if q['question_id'] == question_id:
                if q['score'] > 0:
                    return True
                return False
        return False

    def get_all_scores(self):
        return [{'user': u['username'], 'score': self._count_user_score(u)} for u in self.users]

    def get_list_of_usernames(self):
        return [u["username"] for u in self.users]

    def get_list_of_users_channels(self):
        return [u["channel_name"] for u in self.users]
