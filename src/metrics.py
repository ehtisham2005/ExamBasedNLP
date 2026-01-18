import textstat
import re

def estimate_effort(text):
    """
    Calculates study time based on length, complexity, AND math density.
    Returns: (minutes, difficulty_label, is_math_heavy)
    """
    if not text or len(text) < 100:
        return 5, "Unknown", False  # Minimum 5 mins for any topic

    # 1. Math Detection 🧮
    # We look for words that signal "Slow Down & Think"
    math_signals = [
        'formula', 'equation', 'calculate', 'theorem', 'proof', 'algorithm', 
        'sigma', 'integral', 'derivative', 'matrix', 'logarithm', 
        'step 1', 'step 2', 'complexity', 'O(', '∑'
    ]
    
    math_hits = 0
    lower_text = text.lower()
    for signal in math_signals:
        math_hits += lower_text.count(signal)
    
    # Heuristic: If we find >3 math signals per 1000 chars, it's a technical topic
    is_math_heavy = math_hits > (len(text) / 1000 * 3)

    # 2. Base Reading Speed (WPM)
    # Average student reading speed is ~200 wpm for fiction, but ~100 for textbooks.
    wpm = 130 
    
    # Adjust for Reading Ease (Flesch-Kincaid)
    complexity = textstat.flesch_reading_ease(text)
    if complexity < 50: wpm = 100   # Dense Academic Text
    if complexity < 30: wpm = 70    # Very Hard / Legalistic

    # 3. Calculate Time
    word_count = textstat.lexicon_count(text, removepunct=True)
    minutes = word_count / wpm
    
    # 4. Apply The "Math Penalty"
    # Math takes time to derive/practice, not just read.
    if is_math_heavy:
        minutes = minutes * 1.6  # +60% more time
    
    # Round to nearest 5 mins (cleaner UI)
    minutes = int(5 * round(minutes / 5))
    if minutes < 5: minutes = 5

    # 5. Determine Label
    label = "Easy"
    if complexity < 60: label = "Moderate"
    if complexity < 40 or is_math_heavy: label = "Hard"

    return minutes, label, is_math_heavy