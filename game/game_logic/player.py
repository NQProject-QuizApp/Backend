
class Player:
    def __init__(self, channel_name, username):
        self.channel_name = channel_name
        self.username = username
        self.scores = {}  # self.answers[question_id] = score

    def set_answer(self, question_id, score):
        if not self.scores.get(question_id, None):
            self.scores[question_id] = score
            return True
        return False

    def total_score(self):
        return sum(self.scores.values())

    def is_answer_correct(self, question_id):
        return True if self.scores.get(question_id, 0) > 0 else False

