web: daphne quiz.asgi:application --port $PORT --bind 0.0.0.0 -v2
chatworker: python manage.py runworker --settings=quiz.settings -v2
game-manager: python manage.py runworker game-manager --settings=quiz.settings
