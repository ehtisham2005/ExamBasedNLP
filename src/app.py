import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import pandas as pd
import warnings
import os
from dotenv import load_dotenv # NEW: Auto-loads .env file
from groq import Groq

# --- IMPORTS ---
from loader import load_text_file
from deep_relations import analyze_deep_relations
from fetcher import fetch_topic_content 
from metrics import estimate_effort
from analyzer import calculate_importance
from parser import ExamParser

# Load Environment Variables from .env file immediately
load_dotenv()

warnings.filterwarnings("ignore", category=ResourceWarning)
st.set_page_config(page_title="Exam Guide AI", layout="wide", page_icon="🧠")

# --- API KEY LOGIC ---
# Priority: 1. Sidebar Input (if user types it) -> 2. Environment Variable
env_key = os.getenv("GROQ_API_KEY")
GROQ_API_KEY = env_key # Default to env var

# --- CACHE MANAGEMENT ---
if 'force_refresh' not in st.session_state:
    st.session_state['force_refresh'] = False

@st.cache_data(show_spinner=False)
def get_analysis_dynamic(topics, pyqs_list, refresh_trigger):
    # 1. Relations
    relations = analyze_deep_relations(topics)
    # 2. Importance
    importance = calculate_importance(topics, pyqs_list)
    
    node_metrics = {}
    total_time = 0
    
    # 3. Content Metrics
    for topic in topics:
        content = fetch_topic_content(topic)
        if not content or len(content) < 50:
            content = f"{topic} involves analysis and structural understanding."
        
        mins, diff, is_math = estimate_effort(content)
        node_metrics[topic] = {"time": mins, "difficulty": diff, "is_math": is_math}
        total_time += mins
        
    return relations, importance, node_metrics, total_time

def generate_chat_responses(client, query, context):
    """
    Generator function that yields text chunks from Groq.
    This fixes the 'Raw JSON' issue by extracting just the text.
    """
    system_prompt = """
    You are an expert Professor in Software Engineering. 
    Answer the student's question based STRICTLY on the provided CONTEXT.
    If the answer is not in the context, use your general knowledge but mention that it wasn't in the syllabus.
    - Be concise and exam-focused.
    - If there is a formula, show it clearly (e.g., E = ...).
    - Use bullet points for readability.
    """
    
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # The Working Model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"CONTEXT:\n{context[:6000]}\n\nQUESTION:\n{query}"}
            ],
            temperature=0.5,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        
        # 🪄 THE MAGIC: Extract text from JSON chunks
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        yield f"⚠️ Error: {str(e)}"

# --- MAIN UI ---
st.title("🧠 Generalized Exam Guide AI")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")
    min_strength = st.slider("Connection Strength", 0.0, 1.0, 0.35, 0.05)
    
    st.divider()
    
    # API Key Input - Only show warning if MISSING
    if not GROQ_API_KEY:
        st.warning("⚠️ No API Key found in .env")
        user_key = st.text_input("🔑 Enter Groq API Key", type="password")
        if user_key: GROQ_API_KEY = user_key
    else:
        st.success("✅ API Key Loaded from .env")
    
    if st.button("🗑️ Clear Cache & Retry"):
        try:
            for f in os.listdir("cache_content"):
                os.remove(os.path.join("cache_content", f))
            st.cache_data.clear()
            st.session_state['force_refresh'] = not st.session_state['force_refresh']
            st.success("Cache Cleared!")
        except: pass

# 1. Load Data
parser = ExamParser(syllabus_path="data/syllabus.txt", pyqs_path="data/pyqs.txt")
topics = parser.parse_syllabus()
pyqs_content = parser.parse_pyqs()

if not topics:
    st.error("❌ Data missing.")
    st.stop()

# 2. Execution
with st.spinner("🚀 AI is analyzing context..."):
    relations, importance_scores, node_metrics, total_time = get_analysis_dynamic(topics, pyqs_content, st.session_state['force_refresh'])

# 3. Process Data
df_data = []
for topic in topics:
    raw = importance_scores.get(topic, {"score": 0})
    score = raw.get("score", 0) if isinstance(raw, dict) else 0
    meta = node_metrics.get(topic, {})
    df_data.append({
        "Topic": topic, "Score": score, 
        "Time": meta.get("time", 15), "Difficulty": meta.get("difficulty", "Moderate"),
        "Is_Math": meta.get("is_math", False)
    })
df = pd.DataFrame(df_data)

high_cutoff = df['Score'].quantile(0.85)
med_cutoff = df['Score'].quantile(0.50)
def get_priority(score):
    if score >= high_cutoff and score > 0.1: return "🔴 HIGH"
    if score >= med_cutoff and score > 0.1: return "🟡 MED"
    return "🟢 LOW"
df['Priority'] = df['Score'].apply(get_priority)

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs(["📊 Knowledge Graph & Strategy", "💬 AI Tutor"])

with tab1:
    col_l, col_r = st.columns([3, 1])
    
    with col_l:
        st.subheader("Interactive Knowledge Graph")
        G = nx.Graph()
        for _, row in df.iterrows():
            color = "#ff5733" if row['Priority'] == "🔴 HIGH" else "#ffff00" if row['Priority'] == "🟡 MED" else "#00ff41"
            size = 15 + (row['Score'] * 3)
            G.add_node(row['Topic'], label=row['Topic'], color=color, size=size, title=f"{row['Topic']}\n{row['Priority']}")

        for link in relations:
            if link['score'] >= min_strength:
                G.add_edge(link['topic_a'], link['topic_b'])

        net = Network(height="500px", width="100%", bgcolor="#1e1e1e", font_color="white")
        net.from_nx(G)
        net.force_atlas_2based()
        net.save_graph("graph.html")
        with open("graph.html", 'r', encoding='utf-8') as f:
            components.html(f.read(), height=520)

    with col_r:
        st.subheader("Focus Stats")
        st.metric("Total Topics", len(topics))
        st.metric("Study Time", f"{int(total_time/60)}h {total_time%60}m")
        st.dataframe(df[['Priority', 'Topic', 'Difficulty']], hide_index=True, 
        width='stretch')

with tab2:
    st.header("🤖 Ask the Syllabus")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        # Context Selector
        target_topic = st.selectbox("Select Context Topic:", list(df['Topic']))
        
        # Load Context from Cache
        context_text = ""
        if target_topic:
            content = fetch_topic_content(target_topic)
            if content:
                context_text = content
                st.success(f"✅ Loaded Context for: {target_topic}")
            else:
                st.warning("⚠️ No detailed context found in cache.")

    with c2:
        user_query = st.text_input("Ask a question about this topic:", placeholder=f"Explain {target_topic} with examples...")
        
        if user_query and st.button("🚀 Ask Tutor"):
            if not GROQ_API_KEY:
                st.error("❌ API Key Missing. Please check .env or sidebar.")
            else:
                client = Groq(api_key=GROQ_API_KEY)
                st.write("Generating answer...")
                with st.chat_message("assistant"):
                    # Use st.write_stream with our generator function
                    st.write_stream(generate_chat_responses(client, user_query, context_text))