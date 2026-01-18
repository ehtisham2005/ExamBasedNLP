import os
import re
import hashlib
import time
import trafilatura
from googleapiclient.discovery import build
from dotenv import load_dotenv

# 1. Load environment variables securely
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
CX = os.getenv("SEARCH_ENGINE_ID")

# Safety Check: Stop immediately if keys are missing
if not API_KEY or not CX:
    print("❌ Error: GOOGLE_API_KEY or SEARCH_ENGINE_ID not found.")
    print("   Please create a .env file with your keys.")
    exit(1)

CACHE_DIR = "cache_content"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def clean_topic_for_search(topic):
    """
    Cleans academic titles to make them search-friendly.
    Ex: "Module 1: Overview of SE" -> "Overview of SE"
    """
    # Remove "Module X", "Unit X", "Chapter X"
    topic = re.sub(r'(?i)(module|unit|chapter)\s*\d+[:\.]?', '', topic)
    
    # Smart Split: If comma exists, take the first substantial part
    # Ex: "Nature of Software, Software Process" -> "Nature of Software"
    if ',' in topic:
        parts = topic.split(',')
        if len(parts[0]) > 5:
            topic = parts[0]
            
    # Remove special chars but keep spaces
    topic = re.sub(r'[^a-zA-Z0-9\s]', ' ', topic)
    return topic.strip()

def get_cached_content(topic):
    """Checks if we already downloaded this topic."""
    safe_filename = hashlib.md5(topic.encode()).hexdigest() + ".txt"
    filepath = os.path.join(CACHE_DIR, safe_filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_to_cache(topic, text):
    """Saves content to disk to save API calls later."""
    safe_filename = hashlib.md5(topic.encode()).hexdigest() + ".txt"
    filepath = os.path.join(CACHE_DIR, safe_filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

def fetch_topic_content(topic):
    """
    Main function:
    1. Checks Cache
    2. If missing, uses Google API to find a tutorial
    3. Downloads and extracts the text
    """
    # 1. Check Cache
    cached = get_cached_content(topic)
    if cached:
        print(f"⚡ [Cache Hit] '{topic}'")
        return cached

    clean_query = clean_topic_for_search(topic)
    
    # Refined query for academic depth
    query = f"{clean_query} computer science tutorial detailed explanation"
    
    print(f"🌐 [Google API] Searching: '{clean_query}'...")
    
    try:
        service = build("customsearch", "v1", developerKey=API_KEY)
        
        # 2. Execute Search via API (Limit to 2 results to save quota)
        res = service.cse().list(q=query, cx=CX, num=2).execute()
        results = res.get('items', [])
        
        if not results:
            print("   ❌ No results found via API.")
            return ""

        for item in results:
            url = item['link']
            
            # Skip video/social sites (we want text)
            if any(x in url for x in ["youtube.com", "facebook.com", "quora.com", "reddit.com"]):
                continue
                
            print(f"   🔗 Fetching: {url}")
            
            # 3. Download & Extract
            downloaded = trafilatura.fetch_url(url)
            
            if downloaded:
                text = trafilatura.extract(downloaded)
                
                # Validation: We want at least 500 characters of real content
                if text and len(text) > 500:
                    save_to_cache(topic, text)
                    print(f"   ✅ Success! ({len(text)} chars)")
                    return text
            
            print("   ⚠️  Content extraction failed or too short. Trying next...")
            
    except Exception as e:
        print(f"   ❌ API Error: {e}")
    
    return ""