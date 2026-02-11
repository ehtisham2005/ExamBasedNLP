import os
from sentence_transformers import SentenceTransformer, util
from fetcher import fetch_topic_content
from loader import load_text_file

def analyze_deep_relations(topics):
    """
    Builds a Semantic Knowledge Graph using SBERT.
    Pro Feature: Connects topics based on 'Conceptual Meaning' 
    rather than just sharing keywords.
    """
    print("🕸️  Mapping Semantic Relationships...")
    
    # Use the standard efficient Transformer model
    #model = SentenceTransformer('all-MiniLM-L6-v2')
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # Encode all topics into the semantic vector space
    embeddings = model.encode(topics, convert_to_tensor=True)
    
    # Calculate affinity matrix (How close is every topic to every other topic?)
    cosine_scores = util.cos_sim(embeddings, embeddings)

    relations = []
    num_topics = len(topics)

    # Iterate through the matrix (Upper Triangle only to avoid duplicates)
    for i in range(num_topics):
        for j in range(i + 1, num_topics):
            score = float(cosine_scores[i][j])
            
            # Threshold 0.45: Ensures we only draw edges for Strong connections.
            # (e.g., 'Coupling' <-> 'Cohesion' will pass, 'Coupling' <-> 'Cost' will fail)
            if score > 0.45:
                relations.append({
                    "topic_a": topics[i],
                    "topic_b": topics[j],
                    "score": round(score, 2)
                })
                
    return relations

if __name__ == "__main__":
    # Load your real syllabus
    syllabus_path = "data/syllabus.txt"
    topics = load_text_file(syllabus_path, "Syllabus")
    
    if topics:
        # We test with the first 5 topics to save API quota/time
        # Change [:5] to [:10] if you want a bigger test
        test_batch = topics[:5]
        
        links = analyze_deep_relations(topics)
        
        print("\n🔗 FINAL TOPIC DEPENDENCY REPORT")
        print("="*60)
        
        if not links:
            print("   (No strong connections found. Try lowering threshold in code.)")
            
        for link in links:
            strength_bar = "█" * int(link['score'] * 10)
            print(f"{strength_bar:<10} {link['score']:.2f} | {link['topic_a']} <--> {link['topic_b']}")