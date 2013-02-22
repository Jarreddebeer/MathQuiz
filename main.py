#!/usr/bin/env python
from flask import Flask, render_template, request, make_response
import random
from time import localtime

app = Flask(__name__)


def generate_question(level=0):
    operations = '+-'
    size = 2
    question = (random.randint(1, 15) if i % 2 == 0 else random.choice(operations) for i in xrange(size*2-1))
    return ' '.join(map(str, question))

@app.route('/')
def index():
    return render_template('index.html')

class State:
    QUESTIONS_REMAINING_COOKIE = 'questionsRemaining'
    CORRECTLY_ANSWERED_COOKIE = 'correctlyAnswered'
    INCORRECTLY_ANSWERED_COOKIE = 'incorrectlyAnswered'

    def __init__(self, questionsRemaining = 5, correctlyAnswered = 0, incorrectlyAnswered = 0):
        self.questionsRemaining = questionsRemaining
        self.correctlyAnswered = correctlyAnswered
        self.incorrectlyAnswered = incorrectlyAnswered

    def updateState(self, response):
        response.set_cookie(State.QUESTIONS_REMAINING_COOKIE, self.questionsRemaining)
        response.set_cookie(State.CORRECTLY_ANSWERED_COOKIE, self.correctlyAnswered)
        response.set_cookie(State.INCORRECTLY_ANSWERED_COOKIE, self.incorrectlyAnswered)

    def reset(self):
        self.questionsRemaining = 5
        self.correctlyAnswered = 0
        self.incorrectlyAnswered = 0

    @staticmethod
    def fromCookies(request):
        questionsRemaining = int(request.cookies.get(State.QUESTIONS_REMAINING_COOKIE, 5))
        correctlyAnswered = int(request.cookies.get(State.CORRECTLY_ANSWERED_COOKIE, 0))
        incorrectlyAnswered = int(request.cookies.get(State.INCORRECTLY_ANSWERED_COOKIE, 0))

        return State(questionsRemaining, correctlyAnswered, incorrectlyAnswered)

@app.route('/quiz/<level>', methods=('get', 'post'))
def quiz(**kwargs):
    state = State.fromCookies(request)
    error = ''

    lastQuestion = None
    result = ''
    correctlyAnswered = False

    try:
        lastQuestion = request.form['question']
        result = int(request.form['result'])
        correctlyAnswered = int(lastQuestion) == result
    except KeyError:
        print 'keyerror'
    except ValueError:
        print 'user entered invalid input'
        error += 'Please enter a number as your result'
        lastQuestion = None


    if lastQuestion is not None:
        if correctlyAnswered:
            state.correctlyAnswered += 1
        else:
            state.incorrectlyAnswered += 1


    # number of questions remaining in quiz
    # if we still have to ask questions of the user
    if state.questionsRemaining - 1 != 0:
        question = generate_question()
        answer = eval(question, {}, {})

        response = make_response(render_template('quiz.html',
            numberRemaining=state.questionsRemaining,
            question=question,
            answer=answer,
            error=error,
            answered = result != '', #has the user answered this question
            correct=correctlyAnswered))

        # decrease remaining questions counter if the user answered the question
        if result:
            state.questionsRemaining -= 1
    else:
        response = make_response(render_template('quizComplete.html'))
        state.reset()

    state.updateState(response)
    return response

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html', leaderboard=(('yaseen', '0:05'), ('shuaib parker', '0:05'), ('salaama maniveld', '0:06')))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
