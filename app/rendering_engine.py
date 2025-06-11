from flask import render_template

def render_quiz_question(question_data: dict) -> str:
    """
    Renders a quiz question based on its type.

    Args:
        question_data: A dictionary containing the question details.
                       Expected keys: 'question_type', 'question_text', 'options' (for MCQ).

    Returns:
        An HTML string for the rendered question, or an error message
        if the question type is unsupported.
    """
    question_type = question_data.get('question_type')

    if question_type == "MCQ":
        # Ensure the 'question' variable is passed to the template,
        # which matches the variable name used in mcq_question.html
        return render_template('mcq_question.html', question=question_data)
    else:
        # Log this occurrence for debugging or monitoring
        # import logging
        # logging.warning(f"Unsupported question type encountered: {question_type}")
        return f"<p>Unsupported question type: {question_type}</p>"

if __name__ == '__main__':
    # This part won't run correctly without a Flask app context for render_template.
    # To test this properly, it should be called from within a Flask route.
    # However, we can define some example data for conceptual testing.

    example_mcq_data = {
        "id": "q_python_basics",
        "question_text": "Which of the following is a mutable data type in Python?",
        "question_type": "MCQ",
        "options": ["Tuple", "List", "String", "Integer"],
        "correct_answer": "List", # Not used directly in mcq_question.html rendering but part of the data
        "explanation": "Lists are mutable..." # Same as above
    }

    example_unknown_data = {
        "question_text": "This is a fill-in-the-blanks question.",
        "question_type": "FITB", # Fill In The Blanks
        "parts": ["The capital of France is ____."],
        "correct_answers": ["Paris"]
    }

    print("--- Simulating MCQ Rendering (conceptual) ---")
    # This would typically be: print(render_quiz_question(example_mcq_data))
    # But render_template needs app context.
    print(f"Expected to render 'mcq_question.html' with data: {example_mcq_data}")


    print("\n--- Simulating Unknown Type Rendering ---")
    # This part can be tested directly as it doesn't call render_template
    # However, to call render_quiz_question, we still need app context for Flask.
    # For now, we'll just show the expected output.
    # To test directly:
    # from flask import Flask
    # app = Flask(__name__)
    # with app.app_context():
    #     print(render_quiz_question(example_unknown_data))
    print(f"Expected output for unknown type: <p>Unsupported question type: FITB</p>")
