from sentence_transformers import SentenceTransformer, util
from parser import ExamParser  # Importing the new parser

def calculate_importance(topics, pyqs=None):
    """
    Analyzes topics against a list of parsed PYQs to determine exam priority.
    
    Args:
        topics (list): List of strings representing individual syllabus topics.
        pyqs (list): List of strings representing individual exam questions.
        
    Returns: 
        dict: { "Topic Name": importance_score (0.0 to 5.0+) }
    """
    if not pyqs:
        # If no PYQs provided, everything is equal priority (0)
        return {t: 0 for t in topics}

    print("⚖️  Calculating Topic Importance vs PYQs...")
    # Using 'all-MiniLM-L6-v2' as specified in project status
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 1. Encode Everything
    topic_embeddings = model.encode(topics, convert_to_tensor=True)
    pyq_embeddings = model.encode(pyqs, convert_to_tensor=True)

    # 2. Match Topics to PYQs using Semantic Importance Ranking
    # Result is a Matrix: [Topic_1_Scores, Topic_2_Scores...]
    cosine_scores = util.cos_sim(topic_embeddings, pyq_embeddings)

    importance_scores = {}

    for i, topic in enumerate(topics):
        # Find matches > 0.45 similarity to filter for high relevance
        matches = cosine_scores[i]
        significant_matches = matches[matches > 0.45]
        
        # Score = Sum of similarity scores (Weighted Frequency)
        # Higher scores indicate "High Yield" topics
        total_score = float(significant_matches.sum())
        
        importance_scores[topic] = round(total_score, 2)

    return importance_scores

def get_priority_label(score):
    """Helper to convert numeric importance score to a priority label"""
    if score > 2.5: return "🔴 HIGH"
    if score > 1.0: return "🟡 MEDIUM"
    return "🟢 LOW"

if __name__ == "__main__":
    # Integration with the parser
    parser = ExamParser(syllabus_path="data/syllabus.txt", pyqs_path="data/pyqs.txt")
    
    # Extract clean data structures
    clean_topics = parser.parse_syllabus()
    clean_questions = parser.parse_pyqs()
    
    # Run the analysis
    results = calculate_importance(clean_topics, clean_questions)
    
    # Display results sorted by importance
    print("\n--- Topic Priority Ranking ---")
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    for topic, score in sorted_results:
        label = get_priority_label(score)
        print(f"[{label}] {topic}: {score}")