import logging
import os
import json
from typing import Union, Any
import random # Added random
import google.generativeai as genai
from pydantic import BaseModel, ValidationError, field_validator, ValidationInfo

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for Quiz Question Structures ---

class MCQQuestion(BaseModel):
    id: str
    topic: str
    question_text: str
    question_type: str = "MCQ"
    options: list[str]
    correct_answer: str
    explanation: str | None = None

    @field_validator('question_type')
    @classmethod
    def check_question_type_mcq(cls, value):
        if value != "MCQ":
            raise ValueError('Question type must be "MCQ"')
        return value

    @field_validator('options')
    @classmethod
    def check_options_count(cls, v: list[str]):
        if not (2 <= len(v) <= 5):
            raise ValueError('MCQ options list must contain between 2 and 5 items.')
        return v

    @field_validator('correct_answer')
    @classmethod
    def check_correct_answer_in_options(cls, v: str, info: ValidationInfo):
        options_val = info.data.get('options')
        if options_val and v not in options_val:
            raise ValueError('Correct answer must be one of the provided options.')
        return v

class DragAndDropQuestion(BaseModel):
    id: str
    topic: str
    question_text: str
    question_type: str = "DAD"
    draggable_items: list[str]
    drop_targets: list[str]
    correct_matches: dict[str, str]
    explanation: str | None = None

    @field_validator('question_type')
    @classmethod
    def check_question_type_dad(cls, value):
        if value != "DAD":
            raise ValueError('Question type must be "DAD"')
        return value

    @field_validator('correct_matches')
    @classmethod
    def check_matches_logic(cls, v: dict[str, str], info: ValidationInfo):
        if not v:
            raise ValueError("correct_matches dictionary cannot be empty for a DAD question.")

        draggable_items_set = set(info.data.get('draggable_items', []))
        drop_targets_set = set(info.data.get('drop_targets', []))

        if len(draggable_items_set) < len(v):
            logger.warning("More matches defined than draggable items. Some matches might be ignored.")

        for key, val_match in v.items():
            if key not in draggable_items_set:
                raise ValueError(f"Draggable item '{key}' in correct_matches not found in draggable_items list.")
            if val_match not in drop_targets_set:
                raise ValueError(f"Drop target '{val_match}' in correct_matches not found in drop_targets list.")
        return v

    @field_validator('draggable_items', 'drop_targets')
    @classmethod
    def check_list_not_empty(cls, v: list[str], info: ValidationInfo):
        if not v:
            raise ValueError(f"{info.field_name} list cannot be empty.")
        if len(v) < 2: # Typically DAD questions need at least 2 items/targets
             raise ValueError(f"{info.field_name} list must contain at least 2 items.")
        return v


AnyQuizQuestionModel = Union[MCQQuestion, DragAndDropQuestion]

# --- Fallback Data ---
FALLBACK_PYTHON_MCQ_QUESTION: dict = {
    "id": "q_python_basics_fallback_mcq",
    "topic": "Python Basics",
    "question_text": "Which of the following is a mutable data type in Python? (Fallback MCQ)",
    "question_type": "MCQ",
    "options": ["Tuple", "List", "String", "Integer"],
    "correct_answer": "List",
    "explanation": "Lists are mutable. (This is a fallback MCQ question)",
}

FALLBACK_DAD_QUESTION: dict = {
    "id": "q_geography_fallback_dad",
    "topic": "Geography",
    "question_text": "Match the capital to the country (Fallback DAD):",
    "question_type": "DAD",
    "draggable_items": ["Paris (fallback)", "Berlin (fallback)", "Rome (fallback)"],
    "drop_targets": ["France (fallback)", "Germany (fallback)", "Italy (fallback)"],
    "correct_matches": {
        "Paris (fallback)": "France (fallback)",
        "Berlin (fallback)": "Germany (fallback)",
        "Rome (fallback)": "Italy (fallback)"
    },
    "explanation": "These are major European capitals and their countries. (This is a fallback DAD question)"
}

# --- LLM Interaction ---
def generate_quiz_question(topic: str, preferred_type: str = "ANY") -> dict:
    logger.info(f"Request to generate question for topic: '{topic}', preferred type: '{preferred_type}'")

    question_type_to_generate = preferred_type
    if preferred_type.upper() == "ANY":
        question_type_to_generate = random.choice(["MCQ", "DAD"])

    current_model_schema: type[BaseModel]
    fallback_question_data: dict
    prompt_type_name: str

    if question_type_to_generate.upper() == "MCQ":
        current_model_schema = MCQQuestion
        fallback_question_data = FALLBACK_PYTHON_MCQ_QUESTION.copy()
        prompt_type_name = "Multiple-Choice Question (MCQ)"
    elif question_type_to_generate.upper() == "DAD":
        current_model_schema = DragAndDropQuestion
        fallback_question_data = FALLBACK_DAD_QUESTION.copy()
        prompt_type_name = "Drag-and-Drop Matching Question (DAD)"
    else: # Default to MCQ if preferred_type is invalid
        logger.warning(f"Invalid preferred_type '{preferred_type}'. Defaulting to MCQ.")
        question_type_to_generate = "MCQ"
        current_model_schema = MCQQuestion
        fallback_question_data = FALLBACK_PYTHON_MCQ_QUESTION.copy()
        prompt_type_name = "Multiple-Choice Question (MCQ)"

    logger.info(f"Determined to generate a {question_type_to_generate} question.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning(f"GOOGLE_API_KEY not found. Returning fallback {question_type_to_generate} question for topic '{topic}'.")
        fallback_q = fallback_question_data
        fallback_q['topic'] = topic
        fallback_q['id'] = f"q_{topic.replace(' ', '_').lower()}_fallback_{question_type_to_generate.lower()}"
        fallback_q['question_text'] = f"(API Key Missing) {fallback_q['question_text']}"
        return fallback_q

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')

        # Construct the prompt dynamically
        base_prompt_intro = (
            f"Generate a single {prompt_type_name} about the topic: '{topic}'. "
            "The question should be challenging but fair for a knowledgeable high school student. "
            "Ensure your response is a single, valid JSON object that strictly adheres to the Pydantic model schema provided below. "
            f"The 'topic' field in the JSON should be exactly '{topic}'. "
            f"The 'id' should be a simple, unique snake-case identifier like 'q_{topic.replace(' ', '_').lower()}_{question_type_to_generate.lower()}_<unique_suffix>'. "
        )

        if current_model_schema == MCQQuestion:
            prompt = (
                base_prompt_intro +
                "Provide exactly 4 options for the MCQ. The 'correct_answer' must be one of the strings listed in 'options'. "
                "The 'explanation' should clarify why the correct answer is right and others are wrong.\n"
                f"Pydantic Model Schema for MCQQuestion:\n{MCQQuestion.model_json_schema(indent=2)}"
            )
        elif current_model_schema == DragAndDropQuestion:
            prompt = (
                base_prompt_intro +
                "Provide between 3 to 5 draggable items and a corresponding number of unique drop targets. "
                "The 'correct_matches' dictionary should map text from 'draggable_items' to text from 'drop_targets'. "
                "All draggable items listed must be keys in 'correct_matches' if no distractor items are intended. If you include distractor draggable items, they should not be in `correct_matches` keys. "
                "Similarly, all drop targets listed must be values in `correct_matches` if no distractor targets are intended. "
                "For this request, ensure all listed draggable items have a correct match in the drop_targets, and all drop_targets are used in a match. " # No distractors for now
                "The 'explanation' should provide context or reasoning for the matches.\n"
                f"Pydantic Model Schema for DragAndDropQuestion:\n{DragAndDropQuestion.model_json_schema(indent=2)}"
            )
        else: # Should not happen due to earlier defaulting
            raise ValueError("Unsupported model schema determined.")

        logger.info(f"Sending {question_type_to_generate} request to LLM for topic '{topic}'...")
        # logger.debug(f"Prompt for LLM:\n{prompt}") # Optional: log full prompt

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                # response_schema argument is not directly supported for Pydantic models in generate_content's GenerationConfig.
                # The schema must be part of the textual prompt.
            )
        )

        logger.info(f"LLM {question_type_to_generate} response received. Text length: {len(response.text if response.text else '')}")

        cleaned_response_text = response.text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()

        # Validate using the determined Pydantic model schema
        validated_data = current_model_schema.model_validate_json(cleaned_response_text)
        question_data = validated_data.model_dump()

        # Ensure topic and id are correctly set, overriding LLM if necessary for consistency
        question_data['topic'] = topic
        if not question_data.get('id') or not question_data['id'].startswith(f"q_{topic.replace(' ', '_').lower()}_{question_type_to_generate.lower()}"):
            question_data['id'] = f"q_{topic.replace(' ', '_').lower()}_{question_type_to_generate.lower()}_llm_{hash(question_data['question_text']) % 10000}"

        logger.info(f"Successfully validated LLM {question_type_to_generate} response for topic '{topic}'. Question ID: {question_data['id']}")
        return question_data

    except ValidationError as e:
        logger.error(f"LLM {question_type_to_generate} response JSON validation error for topic '{topic}': {e}")
        raw_response_text = response.text if 'response' in locals() and response.text else "N/A"
        logger.error(f"LLM raw response was: {raw_response_text}")

        fallback_q = fallback_question_data # Use the one determined by question_type_to_generate
        fallback_q['topic'] = topic
        fallback_q['id'] = f"q_{topic.replace(' ', '_').lower()}_validation_fallback_{question_type_to_generate.lower()}"
        fallback_q['question_text'] = f"(Validation Error for {question_type_to_generate}) {fallback_q['question_text']}"
        return fallback_q

    except Exception as e:
        logger.error(f"LLM API call or processing for {question_type_to_generate} failed for topic '{topic}': {type(e).__name__} - {e}")
        if 'response' in locals() and hasattr(response, 'prompt_feedback'):
            logger.error(f"LLM prompt feedback: {response.prompt_feedback}")

        # Fallback to the specific type's fallback data
        fallback_q = fallback_question_data
        fallback_q['topic'] = topic
        fallback_q['id'] = f"q_{topic.replace(' ', '_').lower()}_api_error_fallback_{question_type_to_generate.lower()}"
        fallback_q['question_text'] = f"(API Error for {question_type_to_generate}) {fallback_q['question_text']}"
        return fallback_q

if __name__ == '__main__':
    print("--- Testing LLM Integration with Dynamic Question Types ---")

    # Ensure GOOGLE_API_KEY is set in your environment to run these tests against the API
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY not set. LLM calls will use fallback data and show error messages.")

    topics = ["Famous Inventors", "The Solar System", "Literary Genres"]
    preferred_types = ["MCQ", "DAD", "ANY"]

    for topic in topics:
        for pref_type in preferred_types:
            print(f"\n--- Generating question for Topic: '{topic}', Preferred Type: '{pref_type}' ---")
            question = generate_quiz_question(topic, preferred_type=pref_type)
            print(f"Generated Question Type: {question.get('question_type')}")
            print(json.dumps(question, indent=2))
            # Basic validation of returned structure (not full Pydantic, just to see if it looks right)
            if not all(k in question for k in ['id', 'topic', 'question_text', 'question_type']):
                 print("ERROR: Core question fields missing!")
            if question.get('question_type') == "MCQ" and 'options' not in question:
                 print("ERROR: MCQ question missing 'options'!")
            if question.get('question_type') == "DAD" and 'draggable_items' not in question:
                 print("ERROR: DAD question missing 'draggable_items'!")

    print("\n--- Testing Fallback DAD Question (direct instantiation for structure check) ---")
    try:
        dad_fallback_instance = DragAndDropQuestion.model_validate(FALLBACK_DAD_QUESTION)
        print("DAD Fallback data is valid against Pydantic model.")
        print(dad_fallback_instance.model_dump_json(indent=2))
    except ValidationError as e:
        print(f"ERROR: DAD Fallback data is NOT valid: {e}")

    print("\n--- Testing Fallback MCQ Question (direct instantiation for structure check) ---")
    try:
        mcq_fallback_instance = MCQQuestion.model_validate(FALLBACK_PYTHON_MCQ_QUESTION)
        print("MCQ Fallback data is valid against Pydantic model.")
        print(mcq_fallback_instance.model_dump_json(indent=2))
    except ValidationError as e:
        print(f"ERROR: MCQ Fallback data is NOT valid: {e}")
