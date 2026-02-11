from sentence_transformers import SentenceTransformer, util
import torch

def calculate_importance(topics, pyqs=None):
    """
    NLP Scoring Engine:
    Prioritizes topics by comparing them against Past Year Questions (PYQs).
    """
    if not pyqs or not topics:
        return {t: {"score": 0, "matches": []} for t in topics}

    print("⚖️  Calculating Topic Importance vs PYQs...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    #model = SentenceTransformer('all-mpnet-base-v2')
    
    topic_embeddings = model.encode(topics, convert_to_tensor=True)
    pyq_embeddings = model.encode(pyqs, convert_to_tensor=True)
    cosine_scores = util.cos_sim(topic_embeddings, pyq_embeddings)

    results = {}

    for i, topic in enumerate(topics):
        scores = cosine_scores[i]
        
        # Filter for genuine matches only (> 0.50 similarity)
        valid_indices = (scores > 0.50).nonzero(as_tuple=True)[0]
        
        if len(valid_indices) == 0:
            results[topic] = {"score": 0, "matches": []}
            continue

        valid_scores = scores[valid_indices]
        
        # Top 5 most relevant questions for this topic
        k = min(5, len(valid_scores))
        top_k_values, top_k_indices = torch.topk(valid_scores, k=k)
        
        # Map back to the actual question text
        matched_questions = [pyqs[valid_indices[idx]] for idx in top_k_indices]

        results[topic] = {
            "score": round(float(top_k_values.sum()), 2),
            "matches": matched_questions
        }

    return results