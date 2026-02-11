import os
import re
import time
import hashlib
import logging
import requests
import trafilatura
import wikipediaapi
from ddgs import DDGS
from urllib.parse import urlparse

# --- CONFIGURATION ---
CACHE_DIR = "cache_content"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Setup Logging (So you can see the Agent "Thinking")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - 🤖 %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("Agent")

# --- TOOLS LAYER ---
class KnowledgeTools:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(user_agent='ExamGuide_Agent/2.0', language='en')
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    def search_wikipedia(self, query):
        """Tool: Fetches summaries from Wikipedia."""
        try:
            page = self.wiki.page(query)
            if page.exists():
                # Agent check: Is this disambiguation?
                if "may refer to" in page.summary.lower():
                    return None 
                return page.summary[0:4000]
        except:
            return None
        return None

    def search_web(self, query, max_results=4):
        """Tool: Deep web search using DuckDuckGo."""
        results = []
        try:
            # Random sleep to avoid bot detection (Agent behavior)
            time.sleep(1) 
            with DDGS() as ddgs:
                # We specifically look for "text-heavy" sites
                results = [r for r in ddgs.text(query, max_results=max_results)]
        except Exception as e:
            logger.warning(f"Tool Error (DDG): {e}")
        return results

    def download_page(self, url):
        """Tool: Robust content extractor."""
        try:
            # Filter Blocked Domains
            domain = urlparse(url).netloc
            if any(x in domain for x in ["youtube", "facebook", "reddit", "twitter", "instagram", "tiktok"]):
                return None
            if url.endswith(('.pdf', '.docx', '.pptx')):
                return None

            response = requests.get(url, headers=self.headers, timeout=6)
            if response.status_code != 200: return None
            
            # Use Trafilatura for "Main Content Extraction" (ignores sidebars/ads)
            text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
            return text
        except:
            return None

# --- REASONING LAYER ---
class Validator:
    """The 'Critic'. Judges if content is good enough."""
    
    REQUIRED_KEYWORDS = ["software", "system", "development", "engineering", "coding", "lifecycle", "testing"]
    
    @staticmethod
    def assess_relevance(text, topic):
        if not text or len(text) < 300:
            return False, "Content too short/empty"
            
        text_lower = text.lower()
        topic_lower = topic.lower()
        
        # Check 1: Topic Presence
        # If the topic name isn't in the text, it's likely a wrong redirect
        if topic_lower not in text_lower:
            # Fallback: Check for split parts (e.g. topic="Requirements Elicitation", text has "Elicitation")
            parts = topic_lower.split()
            if not any(part in text_lower for part in parts if len(part) > 3):
                return False, "Topic keywords missing"

        # Check 2: Domain Relevance (Discourse Integrity)
        # Prevents "Product" matching "Shampoo"
        relevance_score = sum(1 for word in Validator.REQUIRED_KEYWORDS if word in text_lower)
        if relevance_score < 2:
            return False, "Domain mismatch (Not SE content)"

        return True, "Valid"

# --- AGENT LAYER ---
class ResearchAgent:
    def __init__(self):
        self.tools = KnowledgeTools()
        self.memory = set() # To avoid repeating failed URLs

    def formulate_strategies(self, topic):
        """
        Planning Step: Generates search strategies based on the topic type.
        """
        clean_topic = re.sub(r'[^a-zA-Z0-9\s]', ' ', topic).strip()
        
        strategies = [
            # 1. Direct Academic Definition
            {"source": "wiki", "query": clean_topic},
            {"source": "wiki", "query": f"{clean_topic} (software)"},
            
            # 2. Contextual Web Search (Standard)
            {"source": "web", "query": f"{clean_topic} software engineering tutorial"},
            
            # 3. Query Expansion (If Standard fails)
            {"source": "web", "query": f"What is {clean_topic} in computer science?"},
            
            # 4. Keyword Drill-down (Last Resort)
            {"source": "web", "query": f"{clean_topic} definition concepts"},
        ]
        return strategies

    def execute_task(self, topic):
        """
        The Main Loop: Reason -> Act -> Observe -> Correct
        """
        file_hash = hashlib.md5(topic.encode()).hexdigest()
        filepath = os.path.join(CACHE_DIR, f"{file_hash}.txt")

        # 1. Check Long-Term Memory (Cache)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                cached_data = f.read()
            if len(cached_data) > 100:
                print(f"🔹 Cache Hit: '{topic}'")
                return cached_data # Return silently if cached

        logger.info(f"🔎 Starting investigation for: '{topic}'")
        strategies = self.formulate_strategies(topic)
        
        for step in strategies:
            source = step["source"]
            query = step["query"]
            
            # logger.info(f"  👉 Trying Strategy: [{source.upper()}] '{query}'")
            
            content = None
            if source == "wiki":
                content = self.tools.search_wikipedia(query)
            
            elif source == "web":
                results = self.tools.search_web(query)
                for res in results:
                    url = res['href']
                    if url in self.memory: continue # Don't retry failed links
                    
                    # logger.info(f"    🔗 Inspecting: {url[:40]}...")
                    fetched_text = self.tools.download_page(url)
                    
                    # CRITICAL STEP: Validation (The Agent checks its own work)
                    is_valid, reason = Validator.assess_relevance(fetched_text, topic)
                    
                    if is_valid:
                        content = fetched_text
                        break
                    else:
                        self.memory.add(url)
                        # logger.warning(f"    ❌ Rejected: {reason}")

            if content:
                logger.info(f"  ✅ Success! Strategy worked. Saving {len(content)} chars.")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return content

        # If all strategies fail
        logger.error(f"  💀 Task Failed: Could not find valid data for '{topic}'")
        with open(filepath, 'w', encoding='utf-8') as f: f.write("") # Tombstone
        return ""

# --- EXPORTED FUNCTION (THIS WAS MISSING) ---
agent = ResearchAgent()

def fetch_topic_content(topic):
    return agent.execute_task(topic)