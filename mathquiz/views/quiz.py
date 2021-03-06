import random
from time import time

from flask import render_template, session, request, flash, make_response
from mathquiz import app, analytics, database, question
from mathquiz.analytics import stats

QUIZ_TIME = 60


@app.route('/quiz/<typee>', methods=('get', 'post'))
def quiz(typee):
    #convert string types to internal enums
    difficulty = question.Difficulties[session['difficulty'].upper()]
    type = question.Types[typee.upper()]
    if type == question.Types.ALL:
        type = random.choice(list(question.Types))
        # looks ugly but we don't want to accidently get ourselves into a
        # semi infinite loop where we always choose Type.ALL do we?
        if type == question.Types.ALL:
            type = question.Types.ADDSUB

    startTime = time()
    try:
        correctlyAnswered = int(session['correctlyAnswered'])
        incorrectlyAnswered = int(session['incorrectlyAnswered'])
        startTime = float(session['startTime'])
    except KeyError:
        # force a new quiz
        session['quizId'] = -1

    previousAnswer, userAnswer, userAnswerCorrect = None, None, None
    scoring = []


    # number of questions remaining in quiz
    # if we still have to ask questions of the user
    timeRemaining = QUIZ_TIME - (time() - startTime)

    if 'quizId' not in session or session['quizId'] == -1:
        session['quizId'] = database.create_quiz(type)
        startTime = session['startTime'] = time()
        timeRemaining = QUIZ_TIME
        correctlyAnswered = session['correctlyAnswered'] = 0
        incorrectlyAnswered = session['incorrectlyAnswered'] = 0
        analytics.track('new_quiz', {'quiz_type': question.Types[typee.upper()]})
        stats.incr('mathchallenge.quiz.new')
        stats.incr('mathchallenge.quiz.new.%s' % typee.upper())

    elif timeRemaining >= 0:
        # if we have already started the quiz
        try:
            previousAnswer = session['previousQuestionAnswer']
            userAnswer = int(request.form['result'])
            userAnswerCorrect = previousAnswer == userAnswer

            score = question.score(type, difficulty, userAnswerCorrect)

            # calculate streak bonus
            streakLength = database.calculate_streak_length(session['userId'], session['quizId'], difficulty)
            streakScore = 0 if streakLength < 3 else 3 + streakLength
            if streakScore != 0 and userAnswerCorrect:
                score += streakScore
                scoring.append('Streak of %d. %d bonus points!' % (streakLength, streakScore))

            database.quiz_answer(session['userId'], session['quizId'], previousAnswer, userAnswer, userAnswerCorrect, score)


            scoring.append('Score: %d points!' % database.cumulative_quiz_score(session['quizId']))
            #analytics.track('quiz_answer', {'quiz':session['quizId'], 'correct':userAnswerCorrect, 'difficulty':difficulty,'type':typee})
            stats.incr('mathchallenge.quiz.answer')
            if userAnswerCorrect:
                correctlyAnswered += 1
            else:
                incorrectlyAnswered += 1
        except (ValueError, KeyError):
            flash('Please enter a number as an answer')

    if timeRemaining >= 0:
        q = question.generateQuestion(type, difficulty)
        session['previousQuestionAnswer'] = q.answer

        response = make_response(
            render_template('quiz.html',
                            question=str(q),
                            scoring=scoring,
                            timeRemaining=int(timeRemaining),
                            #has the user answered this question
                            answered = userAnswer is not None,
                            correct=userAnswerCorrect,
                            correctAnswer=previousAnswer))
    else:
        # calculate score
        numberAnswered = correctlyAnswered+incorrectlyAnswered

        oldHighScore = database.fetch_user_score(session['userId'], difficulty)
        oldLeaderboardPosition = database.fetch_user_rank(session['userId'], difficulty)
        score = database.quiz_complete(difficulty, session['quizId'], typee.lower(), correctlyAnswered, numberAnswered)
        newLeaderboardPosition = database.fetch_user_rank(session['userId'], difficulty)
        leaderboardJump = None
        if oldLeaderboardPosition is not None and newLeaderboardPosition is not None:
            leaderboardJump = oldLeaderboardPosition - newLeaderboardPosition

        analytics.track('quiz_completed', {'quiz': session['quizId'], 'score': score})
        stats.incr('mathchallenge.quiz.completed')
        stats.incr('mathchallenge.quiz.completed.%s' % difficulty)
        # reset quiz
        session['quizId'] = -1

        newDifficulty = False
        # if user answered > 80% of answers correctly and answered > 10 correctly increase difficulty level
        if numberAnswered >= 5 and (float(correctlyAnswered) / numberAnswered) >= 0.8:
            newDifficultyIndex = question.Difficulties.index(session['difficulty'].upper())+1
            # don't go over max difficulty (hard)
            if newDifficultyIndex < len(question.Difficulties) \
                    and newDifficultyIndex > question.Difficulties.index(database.fetch_user_difficulty(session['userId'])):
                if question.Types[typee.upper()] == question.Types.ALL:
                    newDifficulty = question.Difficulties[newDifficultyIndex].lower()
                    analytics.track('difficulty_increased', {'new_difficulty': newDifficulty})
                    stats.incr('mathchallenge.user.difficulty_increased')
                    stats.incr('mathchallenge.user.difficulty_increased.%s'%newDifficulty)
                    database.set_user_difficulty(session['userId'], newDifficultyIndex)
                    session['difficulty'] = question.Difficulties[newDifficultyIndex]
                else:
                    flash('You are good enough at this section to be on another level. Show us your skills at Badass mode to level up')


        response = make_response(
            render_template('quizComplete.html',
                            correct=userAnswerCorrect,
                            numberCorrect=correctlyAnswered,
                            newDifficulty=newDifficulty,
                            oldHighScore=oldHighScore,
                            score=score,
                            leaderboardJump=leaderboardJump,
                            total=correctlyAnswered+incorrectlyAnswered))


    # persist changes to session
    session['correctlyAnswered'] = correctlyAnswered
    session['incorrectlyAnswered'] = incorrectlyAnswered

    return response
