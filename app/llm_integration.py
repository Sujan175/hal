import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)

def generate_quiz_question(topic: str) -> dict:
    """
    Generates a quiz question for a given topic.
    Currently, this function returns a hardcoded placeholder.
    In the future, it will interact with an LLM to generate questions.
    """
    logging.info(f"LLM Interaction: Using placeholder for topic '{topic}'. Real LLM call not yet implemented.")

    # Hardcoded example question (more generic)
    # This simulates a question that an LLM might generate based on the topic.
    # For a topic like "Python Basics":
    if topic.lower() == "python basics":
        question_data = {
            "question_text": "Which of the following is a mutable data type in Python?",
            "question_type": "MCQ",
            "options": ["Tuple", "List", "String", "Integer"],
            "correct_answer": "List",
            "explanation": "Lists are mutable, meaning their contents can be changed after creation. Tuples and Strings are immutable."
        }
    # For a topic like "Addition":
    elif topic.lower() == "addition":
        question_data = {
            "question_text": "What is 5 + 7?",
            "question_type": "MCQ",
            "options": ["10", "11", "12", "13"],
            "correct_answer": "12",
            "explanation": "Adding 5 and 7 results in 12."
        }
    # Generic fallback if topic doesn't match specific examples
    else:
        question_data = {
            "question_text": f"What is a fundamental concept related to '{topic}'?",
            "question_type": "MCQ",
            "options": [f"Placeholder Option A for {topic}", f"Placeholder Option B for {topic}", f"Placeholder Option C for {topic}", f"Placeholder Option D for {topic}"],
            "correct_answer": f"Placeholder Option A for {topic}",
            "explanation": f"This is a placeholder explanation for why Option A is correct for the topic '{topic}'."
        }

    # Add a unique ID to the question for potential future use (e.g., tracking answers)
    # For simplicity, we can use a hash of the question text or a random number,
    # but for now, a fixed ID for the placeholder is fine.
    question_data["id"] = "q_" + topic.lower().replace(" ", "_") # Example: "q_python_basics"
    question_data["topic"] = topic # Include the original topic

    return question_data

if __name__ == '__main__':
    # Example usage:
    print("Example for 'Python Basics':")
    print(generate_quiz_question("Python Basics"))
    print("\nExample for 'Addition':")
    print(generate_quiz_question("Addition"))
    print("\nExample for 'General Topic':")
    print(generate_quiz_question("General Topic"))
