from sentence_transformers import SentenceTransformer, util
from loader import load_text_file

def calculate_importance(topics, pyqs_path="data/pyqs.txt"):
    """
    Analyzes topics against PYQs to determine exam priority.
    Returns: dict { "Topic Name": importance_score (0.0 to 5.0+) }
    """
    # 1. Load PYQs
    pyqs = load_text_file(pyqs_path, "PYQs")
    if not pyqs:
        # If no PYQs found, everything is equal priority (0)
        return {t: 0 for t in topics}

    print("⚖️  Calculating Topic Importance vs PYQs...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 2. Encode Everything
    topic_embeddings = model.encode(topics, convert_to_tensor=True)
    pyq_embeddings = model.encode(pyqs, convert_to_tensor=True)

    # 3. Match Topics to PYQs
    # Result is a Matrix: [Topic_1_Scores, Topic_2_Scores...]
    cosine_scores = util.cos_sim(topic_embeddings, pyq_embeddings)

    importance_scores = {}

    for i, topic in enumerate(topics):
        # Find matches > 0.40 similarity
        matches = cosine_scores[i]
        significant_matches = matches[matches > 0.45]
        
        # Score = Sum of similarity scores (Weighted Frequency)
        # Example: If a topic matches 3 questions with 0.8 similarity, score is 2.4
        total_score = float(significant_matches.sum())
        
        importance_scores[topic] = round(total_score, 2)

    return importance_scores

def get_priority_label(score):
    """Helper to convert number score to text label"""
    if score > 2.5: return "🔴 HIGH"
    if score > 1.0: return "🟡 MEDIUM"
    return "🟢 LOW"