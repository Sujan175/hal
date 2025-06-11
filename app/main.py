from flask import Flask, render_template, request, session, redirect, url_for
from .llm_integration import generate_quiz_question
from .rendering_engine import render_quiz_question

app = Flask(__name__)
# It's crucial to set a secret key for session management.
# In a real application, use a strong, randomly generated key stored securely.
app.secret_key = 'dev_secret_key_for_quiz_app'


@app.route('/')
def index():
    """
    Renders the topic selection page.
    """
    return render_template('index.html')


@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    """
    Starts a new quiz based on the selected topic.
    - Gets the topic from the form.
    - Generates the first question.
    - Stores question data and topic in session.
    - Renders the quiz page.
    """
    if request.method == 'POST':
        topic = request.form.get('topic')
        if not topic:
            # Handle case where topic is missing, though 'required' in HTML should prevent this
            return redirect(url_for('index'))

        question_data = generate_quiz_question(topic)

        session['current_question'] = question_data
        session['current_topic'] = topic # Store the topic for the "Next Question" feature
        session.pop('feedback', None) # Clear any old feedback

        question_html = render_quiz_question(question_data)
        return render_template('quiz_page.html', question_html=question_html)

    # If GET request or other, redirect to index
    return redirect(url_for('index'))


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """
    Processes the submitted answer for the current question.
    - Retrieves current question from session.
    - Compares submitted answer with the correct answer.
    - Stores feedback in session.
    - Redirects to the feedback display page.
    """
    current_question = session.get('current_question')
    if not current_question:
        return redirect(url_for('index')) # No active question

    selected_answer = request.form.get('answer')
    submitted_question_id = request.form.get('question_id')

    # Basic validation
    if not selected_answer or not submitted_question_id:
        # Handle incomplete form submission, perhaps redirect back to the question
        # For now, redirecting to index or showing an error might be suitable
        session['feedback'] = "Please select an answer."
        return redirect(url_for('show_feedback'))


    if submitted_question_id != current_question.get('id'):
        # Question ID mismatch, could be an old tab or session issue
        session['feedback'] = "There was an issue with the question. Please try the current one."
        # Potentially regenerate question or redirect to index
        return redirect(url_for('index')) # Or a specific error page

    is_correct = (selected_answer == current_question.get('correct_answer'))

    if is_correct:
        session['feedback'] = "Correct!"
    else:
        explanation = current_question.get('explanation', 'No explanation provided.')
        correct_ans_text = current_question.get('correct_answer', 'N/A')
        session['feedback'] = f"Incorrect. The correct answer was: {correct_ans_text}. Explanation: {explanation}"

    return redirect(url_for('show_feedback'))


@app.route('/show_feedback')
def show_feedback():
    """
    Displays feedback for the submitted answer and the question again.
    - Retrieves feedback and current question from session.
    - Renders the quiz page, which will show the feedback.
    """
    feedback = session.get('feedback') # Don't pop here, let quiz_page display it
    current_question = session.get('current_question')

    if not current_question: # If there's no question, no point showing feedback page
        return redirect(url_for('index'))

    # We need to re-render the question to display alongside the feedback
    question_html = render_quiz_question(current_question)

    # The quiz_page.html template will be responsible for displaying the feedback.
    # And a "Next Question" button.
    return render_template('quiz_page.html', question_html=question_html, feedback=feedback)


@app.route('/next_question')
def next_question():
    """
    Loads the next question for the current topic.
    - Retrieves current topic from session.
    - Generates a new question.
    - Updates session with the new question.
    - Renders the quiz page with the new question.
    """
    current_topic = session.get('current_topic')
    if not current_topic:
        # If no topic is stored, redirect to start a new quiz
        return redirect(url_for('index'))

    question_data = generate_quiz_question(current_topic)
    session['current_question'] = question_data
    session.pop('feedback', None)  # Clear old feedback before showing a new question

    question_html = render_quiz_question(question_data)
    return render_template('quiz_page.html', question_html=question_html)


if __name__ == '__main__':
    # Note: Using host='0.0.0.0' makes the app accessible externally if needed.
    # Port 5001 is used as specified previously.
    app.run(debug=True, host='0.0.0.0', port=5001)
