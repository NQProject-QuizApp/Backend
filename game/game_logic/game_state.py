
class GameState:
    def __init__(self, code):
        self.code = code
        self.users = []
        self.running = False
        self.current_question = None

    def start_game(self):
        if self.running:
            return False
        self.running = True
        return True

    def is_game_running(self):
        return self.running

    def is_username_available(self, username):
        for u in self.users:
            if u["username"] == username:
                return False
        return True

    def add_user(self, channel_name, username):
        if not self.is_username_available(username):
            index = 2
            while not self.is_username_available(username + f" #{index}"):
                index += 1
            username = username + f" #{index}"
        self.users.append({"channel_name": channel_name, 'username': username, "answers": []})
        return username

    def remove_user(self, channel_name):
        self.users.remove(self.get_user(channel_name))
        return

    def get_user(self, channel_name):
        for u in self.users:
            if u["channel_name"] == channel_name:
                return u
        return None

    def count_user_score(self, user):
        score = 0
        for q in user['answers']:
            score += q['score']
        return score

    def set_answer(self, channel_name, question_id, score):
        user = self.get_user(channel_name)
        for q in user['answers']:
            if q['question_id'] == question_id:
                return False
        user['answers'].append({"question_id": question_id, "score": score})
        return True

    def check_if_user_was_right(self, channel_name, question_id):
        user = self.get_user(channel_name)
        for q in user['answers']:
            if q['question_id'] == question_id:
                if q['score'] > 0:
                    return True
                return False
        return False

    def get_all_scores(self):
        return [{'user': u['username'], 'score': self.count_user_score(u)} for u in self.users]

    def get_list_of_usernames(self):
        return [u["username"] for u in self.users]

    def get_list_of_users_channels(self):
        return [u["channel_name"] for u in self.users]
