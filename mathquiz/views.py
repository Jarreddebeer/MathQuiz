#!/usr/bin/env python
from flask import render_template, request, make_response, session, redirect, url_for, flash
import random
from time import time

from . import app

import config
import question
import database

@app.route('/user/set_username', methods=('get', 'post'))
def set_username():
    if 'username' in request.form:
        username = request.form['username']
        if database.username_exists(username):
            return render_template('set_username.html', username_exists = username)
        else:
            session['username'] = username
            database.set_username(username)
            return redirect('/')
    else:
        return render_template('set_username.html')

@app.route('/')
def index():
    session['quizId'] = -1

    # if the user has not given us a username we should probably ask for one
    if not session.has_key('username') or session['username'] is None:
       return redirect('/user/set_username')

    return render_template('index.html',
            username=session['username'],
            difficulty='Easy',
        )


@app.route('/quiz/<typee>/<difficulty>', methods=('get', 'post'))
def quiz(typee, difficulty):
    #convert string types to internal enums
    difficulty = question.Difficulties[difficulty.upper()]
    type = question.Types[typee.upper()]

    try:
        questionsRemaining = int(session['questionsRemaining'])
        correctlyAnswered = int(session['correctlyAnswered'])
        incorrectlyAnswered = int(session['incorrectlyAnswered'])
        startTime = float(session['startTime'])
    except KeyError:
        # force a new quiz
        session['quizId'] = -1

    previousAnswer, userAnswer, userAnswerCorrect = None, None, None

    if 'quizId' not in session or session['quizId'] == -1:
        quizId = session['quizId'] = database.create_quiz(type)
        startTime = session['startTime'] = time()
        questionsRemaining = session['questionsRemaining'] = 5
        correctlyAnswered = session['correctlyAnswered'] = 0
        incorrectlyAnswered = session['incorrectlyAnswered'] = 0

    else:
        # if we have already started the quiz
        try:
            previousAnswer = session['previousQuestionAnswer']
            userAnswer = int(request.form['result'])
            userAnswerCorrect = previousAnswer == userAnswer

            database.log_quiz_answer(session['quizId'], previousAnswer, userAnswer, userAnswerCorrect)
            if userAnswerCorrect:
               correctlyAnswered += 1
            else:
               incorrectlyAnswered += 1
        except (ValueError, KeyError):
            flash('Please enter a number as an answer')

    # number of questions remaining in quiz
    # if we still have to ask questions of the user
    if questionsRemaining - 1 != 0:
        q = question.generateQuestion(type, difficulty)
        session['previousQuestionAnswer'] = q.answer

        response = make_response(render_template('quiz.html',
            numberRemaining=questionsRemaining,
            question=str(q),
            answered = userAnswer is not None, #has the user answered this question
            correct=userAnswerCorrect))

        # decrease remaining questions counter if the user answered the question
        if userAnswer is not None:
            questionsRemaining -= 1
    else:
        scoreMultipliers = {question.Difficulties.EASY: 1, question.Difficulties.MEDIUM: 2, question.Difficulties.HARD: 3}
        score = max(0, 10*correctlyAnswered * scoreMultipliers[difficulty] - 5 * incorrectlyAnswered)
        print session['quizId']

        database.quiz_complete(session['quizId'], correctlyAnswered, correctlyAnswered+incorrectlyAnswered, score)
        response = make_response(render_template('quizComplete.html',
            correct=userAnswerCorrect,
            numberCorrect=correctlyAnswered,
            total=correctlyAnswered+incorrectlyAnswered,
            time=round(time()-startTime, 1)))

        session['quizId'] = -1


    # persist changes to session
    session['questionsRemaining'] = questionsRemaining
    session['correctlyAnswered'] = correctlyAnswered
    session['incorrectlyAnswered'] = incorrectlyAnswered

    return response

@app.route('/leaderboard', defaults={'page': 0})
@app.route('/leaderboard/<int:page>')
def leaderboard(page):
    return render_template('leaderboard.html', leaderboard=database.leaderboard(page))
