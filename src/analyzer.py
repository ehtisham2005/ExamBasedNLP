from sentence_transformers import SentenceTransformer, util
import torch
import logging

# Configure logging to match the rest of the Pro system
logger = logging.getLogger(__name__)

def calculate_importance(topics, pyqs=None):
    """
    Universal NLP Scoring Engine:
    Prioritizes topics for ANY subject by semantically matching syllabus items 
    against a list of individual Past Year Questions (PYQs).
    
    Args:
        topics (list): List of cleaned syllabus topics from ExamParser.
        pyqs (list): List of individual question blocks from ExamParser.
        
    Returns:
        dict: { "Topic": {"score": float, "matches": list} }
    """
    # 1. Handle empty inputs gracefully for subject-agnostic support
    if not pyqs or not topics:
        logger.warning("Analyzer received empty topics or PYQs list.")
        return {t: {"score": 0, "matches": []} for t in topics}

    print("⚖️  Calculating Topic Importance vs PYQs...")
    
    # 2. Load the High-Accuracy Model
    # Using 'all-mpnet-base-v2' provides better semantic nuance across 
    # different academic domains compared to the lightweight version.
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # 3. Generate Semantic Embeddings
    topic_embeddings = model.encode(topics, convert_to_tensor=True)
    pyq_embeddings = model.encode(pyqs, convert_to_tensor=True)
    
    # 4. Compute Similarity Matrix (Topics x Questions)
    cosine_scores = util.cos_sim(topic_embeddings, pyq_embeddings)

    results = {}

    for i, topic in enumerate(topics):
        scores = cosine_scores[i]
        
        # 5. Filter for Genuine Matches
        # Threshold (0.45-0.50) identifies clear relevance in any subject.
        # We use 0.45 here to catch more subtle cross-subject matches.
        valid_indices = (scores > 0.45).nonzero(as_tuple=True)[0]
        
        if len(valid_indices) == 0:
            results[topic] = {"score": 0.0, "matches": []}
            continue

        valid_scores = scores[valid_indices]
        
        # 6. Extract Top Matches
        # We take the top 5 matches to avoid score bloating from 
        # generic keywords while highlighting the most relevant context.
        k = min(5, len(valid_scores))
        top_k_values, top_k_indices = torch.topk(valid_scores, k=k)
        
        # Map indices back to original question text for the UI "Explorer" tab
        matched_questions = [pyqs[valid_indices[idx]] for idx in top_k_indices]

        # 7. Calculate Final Importance Score
        # Summing similarity values provides a "Weighted Frequency" metric.
        # High Score = Topic appears frequently or very specifically in exams.
        results[topic] = {
            "score": round(float(top_k_values.sum()), 2),
            "matches": matched_questions
        }

    logger.info(f"Analysis complete for {len(topics)} topics against {len(pyqs)} questions.")
    return results

if __name__ == "__main__":
    # Quick Test Case
    test_topics = ["Binary Trees", "Sorting Algorithms", "Thermodynamics"]
    test_pyqs = [
        "Explain the process of traversing a binary tree.",
        "Compare different sorting algorithms like QuickSort and MergeSort.",
        "What are the laws of Thermodynamics?"
    ]
    test_results = calculate_importance(test_topics, test_pyqs)
    print(test_results)