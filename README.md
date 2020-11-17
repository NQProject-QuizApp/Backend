# Backend for QuizApp
Backend for quiz application.

## How to prepare environment?

#### Python:
* Python 3.7 or newer required. 
* To install ale required dependencies: `pip install -r requirements.txt`

#### Docker:
Channels features require Redis to run. This can be achieved with Docker.

Download and install Docker from here: https://www.docker.com/get-started

## How to run the server?
* Redis needs to be running: `docker run -p 6379:6379 -d redis:5`
* Logic of the game is handled by separate worker. To start the worker: `manage.py runworker game-manager`
* To start the server: `manage.py runserver`

## Debug tool for testing communication

Here you can test communication with the server: http://127.0.0.1:8000/game/requests_form_debug

