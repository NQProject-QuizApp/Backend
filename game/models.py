from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.forms import SimpleArrayField
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms import Textarea
from django_mysql.models import ListCharField

ANSWER_LENGTH = 50
AMOUNT_OF_ANSWERS = 4


class Question(models.Model):
    content = models.CharField(max_length=100)
    # answers = ListCharField(base_field=models.CharField(max_length=ANSWER_LENGTH), size=AMOUNT_OF_ANSWERS,
    #                         max_length=AMOUNT_OF_ANSWERS*ANSWER_LENGTH + AMOUNT_OF_ANSWERS - 1, delimiter='|')
    answer0 = models.CharField(max_length=100)
    answer1 = models.CharField(max_length=100)
    answer2 = models.CharField(max_length=100)
    answer3 = models.CharField(max_length=100)
    correct_answer = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(3)])

    @property
    def answers(self):
        return [self.answer0, self.answer1, self.answer2, self.answer3]

    def get_dict(self):
        return {
            'content': self.content,
            'answers': [self.answer0, self.answer1, self.answer2, self.answer3],
        }

    def __str__(self):
        return self.content
