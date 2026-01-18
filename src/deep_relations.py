import os
from sentence_transformers import SentenceTransformer, util
from fetcher import fetch_topic_content
from loader import load_text_file

def analyze_deep_relations(topics):
    print(f"\n🧠 Starting Deep Content Analysis on {len(topics)} topics...")
    
    valid_topics = []
    topic_contents = []
    
    # 1. FETCHING PHASE
    print("\n--- PHASE 1: GATHERING INTELLIGENCE ---")
    for topic in topics:
        # This uses your new Google API fetcher
        content = fetch_topic_content(topic)
        
        # We only analyze topics where we found good data (>500 chars)
        if content and len(content) > 500:
            topic_contents.append(content)
            valid_topics.append(topic)
        else:
            print(f"⚠️  Skipping '{topic}' (Insufficient data)")

    if not valid_topics:
        print("❌ Critical Error: No valid content content fetched.")
        return []

    # 2. AI ANALYSIS PHASE
    print("\n--- PHASE 2: CALCULATING SEMANTIC OVERLAP ---")
    print("Loading AI Model (this takes 2 seconds)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Encode the FULL TEXT content (not just titles)
    embeddings = model.encode(topic_contents, convert_to_tensor=True)
    
    # Compare every topic against every other topic
    cosine_scores = util.cos_sim(embeddings, embeddings)
    
    relations = []
    
    print("\n🔍 DEBUG: Raw Similarity Scores (Internal Logic)")
    print("-" * 50)
    
    for i in range(len(valid_topics)):
        for j in range(i + 1, len(valid_topics)):
            score = float(cosine_scores[i][j])
            
            # Print the raw score so you know the AI is working
            # Truncate titles to keep the console clean
            t1 = (valid_topics[i][:20] + '..') if len(valid_topics[i]) > 20 else valid_topics[i]
            t2 = (valid_topics[j][:20] + '..') if len(valid_topics[j]) > 20 else valid_topics[j]
            
            print(f"   {t1:<22} vs {t2:<22} = {score:.4f}")
            
            # Threshold: 0.30 is a good balance for "Related Concepts"
            if score > 0.30:
                relations.append({
                    "topic_a": valid_topics[i],
                    "topic_b": valid_topics[j],
                    "score": score
                })
    
    # Sort by strongest connection first
    relations.sort(key=lambda x: x['score'], reverse=True)
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