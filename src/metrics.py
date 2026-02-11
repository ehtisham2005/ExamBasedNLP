import re

def analyze_linguistic_features(text):
    text = text.lower()
    words = text.split()
    total_words = len(words)
    if total_words == 0: return 0, 0, 0

    # 1. Math Symbols (Excluding common punctuation)
    # We count =, +, *, /, <, >
    math_symbols = re.findall(r'[=\+\-\*/\^<>≤≥≈]', text)
    symbol_density = len(math_symbols) / len(text) if len(text) > 0 else 0

    # 2. Operational Verbs
    op_verbs = {"calculate", "compute", "derive", "solve", "minimize", "maximize", "estimate"}
    op_hits = sum(1 for w in words if w in op_verbs)
    
    # 3. Formula Patterns (e.g., "E = MC^2")
    # IGNORES years (e.g. 1999) to prevent History being marked as Math
    formula_matches = len(re.findall(r'\b[a-z]\s*=\s*[a-z0-9]', text))

    return symbol_density, op_hits, formula_matches

def estimate_effort(content):
    if not content or len(content.strip()) < 100:
        return 0, "⚠️ No Data", False

    symbol_density, op_hits, formula_matches = analyze_linguistic_features(content)
    
    # --- CLASSIFICATION LOGIC ---
    is_math = False
    
    # Rule A: Strong Formula Evidence
    if formula_matches >= 2: 
        is_math = True
    # Rule B: High Symbol Density + Verbs
    elif symbol_density > 0.008 and op_hits >= 2:
        is_math = True
    # Rule C: Explicit keywords
    elif "formula" in content.lower() and "calculate" in content.lower():
        is_math = True

    # --- TIME ESTIMATION (CAPPED) ---
    word_count = len(content.split())
    # Reading speed: 200 wpm. Cap at 45 mins max to avoid outliers.
    raw_mins = 5 + (word_count // 200)
    mins = min(raw_mins, 45) 

    # --- DIFFICULTY ---
    if is_math:
        difficulty = "Hard" if mins > 25 else "Moderate"
    else:
        if mins > 35: difficulty = "Hard"
        elif mins > 15: difficulty = "Moderate"
        else: difficulty = "Easy"

    return mins, difficulty, is_math