import re

def estimate_effort(content):
    """
    Estimates study time, difficulty, and math intensity based on the content text.
    
    Returns:
        mins (int): Estimated minutes to study.
        difficulty (str): "Easy", "Moderate", or "Hard".
        is_math (bool): True if the topic involves calculations/formulas.
    """
    if not content:
        return 15, "Moderate", False  # Default values if no content

    # 1. Estimate Time (Roughly 150 words per minute reading/study speed)
    word_count = len(content.split())
    # Base time is 10 mins, plus 1 min for every 100 words
    mins = 10 + (word_count // 100)

    # 2. Check for Math/Formulas
    # Keywords that suggest mathematical or derivation-heavy content
    math_keywords = [
        "equation", "formula", "calculate", "derive", "theorem", 
        "integral", "matrix", "probability", "compute", "solve"
    ]
    math_score = sum(1 for word in math_keywords if word in content.lower())
    is_math = math_score > 2  # If more than 2 math words appear, it's math-heavy

    # 3. Estimate Difficulty
    # Longer content + Math usually equals harder
    if is_math and mins > 30:
        difficulty = "Hard"
    elif mins > 20:
        difficulty = "Moderate"
    elif is_math:
        difficulty = "Moderate" # Short but mathy
    else:
        difficulty = "Easy"

    return mins, difficulty, is_math