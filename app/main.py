from flask import Flask, render_template, request, session, redirect, url_for
from .llm_integration import generate_quiz_question, DragAndDropQuestion # Added DragAndDropQuestion
from .rendering_engine import render_quiz_question
import json # Added json import

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
        return redirect(url_for('index'))

    submitted_question_id = request.form.get('question_id')
    question_type = request.form.get('question_type', current_question.get('question_type')) # Get type from form or session

    if not submitted_question_id or submitted_question_id != current_question.get('id'):
        session['feedback'] = "There was an issue with the question submission. Please try again."
        return redirect(url_for('index'))

    feedback_message = "No feedback generated."

    if question_type == "MCQ":
        selected_answer = request.form.get('answer')
        if not selected_answer:
            session['feedback'] = "Please select an answer for the MCQ."
            # Redirect to show_feedback, which will re-render the question
            return redirect(url_for('show_feedback'))

        is_correct = (selected_answer == current_question.get('correct_answer'))
        explanation = current_question.get('explanation', 'No explanation provided.')
        correct_ans_text = current_question.get('correct_answer', 'N/A')

        if is_correct:
            feedback_message = f"Correct! {explanation}"
        else:
            feedback_message = f"Incorrect. The correct answer was: {correct_ans_text}. Explanation: {explanation}"

    elif question_type == "DAD":
        user_dad_answers_json = request.form.get('dad_answers')
        try:
            user_matches = json.loads(user_dad_answers_json) if user_dad_answers_json else {}
        except json.JSONDecodeError:
            user_matches = {}
            logger.error(f"Error decoding DAD answers JSON: {user_dad_answers_json} for question ID {submitted_question_id}")
            session['feedback'] = "There was an error processing your DAD answers. Please try again."
            return redirect(url_for('show_feedback'))

        correct_matches = current_question.get('correct_matches', {})
        if not correct_matches:
            logger.error(f"No correct_matches found in session for DAD question ID {submitted_question_id}")
            session['feedback'] = "Could not evaluate DAD question: missing correct answer data."
            return redirect(url_for('show_feedback'))

        num_correct = 0
        num_total_possible = len(correct_matches)
        feedback_details = []

        # Iterate through all draggable items defined in the question to check their status
        all_draggable_items = current_question.get('draggable_items', [])

        for item in all_draggable_items:
            correct_target = correct_matches.get(item) # Target where this item SHOULD be
            user_target = user_matches.get(item)       # Target where user PLACED this item

            if correct_target: # This item is part of the defined correct matches
                if user_target == correct_target:
                    num_correct += 1
                    feedback_details.append(f"<li>Correct: '{item}' &rarr; '{correct_target}'</li>")
                elif user_target: # User placed it, but on the wrong target
                    feedback_details.append(f"<li>Incorrect: '{item}' placed on '{user_target}', should be '{correct_target}'</li>")
                else: # User did not place this item on any target
                    feedback_details.append(f"<li>Missed: '{item}' should go to '{correct_target}'</li>")
            elif user_target: # Item is a distractor and user placed it
                 feedback_details.append(f"<li>Distractor: '{item}' placed on '{user_target}' (this item had no correct target).</li>")
            # If an item is a distractor and not placed, it's implicitly correct, so no feedback for it.

        # Refine feedback message
        if num_total_possible == 0 and not all_draggable_items : # Should not happen with valid questions
             feedback_message = "This DAD question seems to be empty or misconfigured."
        elif num_correct == num_total_possible and num_total_possible > 0 :
            feedback_message = f"Excellent! All {num_total_possible} matches are correct."
            if feedback_details:
                 feedback_message += "<ul>" + "".join(feedback_details) + "</ul>"
        elif num_correct > 0:
            feedback_message = f"Good effort! You got {num_correct} out of {num_total_possible} primary matches correct."
            if feedback_details:
                 feedback_message += "<ul>" + "".join(feedback_details) + "</ul>"
        else: # num_correct == 0 (and num_total_possible > 0)
            feedback_message = f"Needs improvement. None of the {num_total_possible} primary matches were correct."
            if feedback_details:
                 feedback_message += "<ul>" + "".join(feedback_details) + "</ul>"

        explanation = current_question.get('explanation')
        if explanation:
            feedback_message += f"<p><strong>Overall Explanation:</strong> {explanation}</p>"

    else:
        feedback_message = "Unsupported question type encountered during submission."
        logger.warning(f"Unsupported question type '{question_type}' for question ID {submitted_question_id}")

    session['feedback'] = feedback_message
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


# Temporary test route for DAD rendering
@app.route('/test_dad_render')
def test_dad_render():
    sample_dad_question = DragAndDropQuestion(
        id="dad_test_1",
        topic="Animals",
        question_text="Match the animal to its primary sound:",
        question_type="DAD", # Ensure this is set if not relying on default
        draggable_items=["Dog", "Cat", "Cow", "Duck"],
        drop_targets=["Barks", "Meows", "Moos", "Quacks"],
        correct_matches={"Dog": "Barks", "Cat": "Meows", "Cow": "Moos", "Duck": "Quacks"},
        explanation="These are common sounds made by these animals."
    )
    question_dict = sample_dad_question.model_dump()

    # Render the question using the existing engine
    # The engine will then select 'dad_question.html'
    question_html = render_quiz_question(question_dict)

    # For a more complete page view, embed it within quiz_page.html or similar
    # For now, returning raw HTML is fine for quick inspection,
    # but to see it with styles, better to render a full page.
    # return question_html
    return render_template('quiz_page.html', question_html=question_html, feedback="Test DAD Question")
