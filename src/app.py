import streamlit as st
import os
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import pandas as pd

# Import our modules
from loader import load_text_file
from deep_relations import analyze_deep_relations
from fetcher import get_cached_content
from metrics import estimate_effort
from analyzer import calculate_importance

# --- CONFIG ---
st.set_page_config(page_title="Exam Guide AI", layout="wide")

# --- HELPER: Fix the Icons ---
def get_clean_priority_label(score):
    if score > 2.5: return "🔥🔥🔥 High"
    if score > 1.0: return "🔥🔥 Med"
    return "🔹 Low"

# --- CACHED FUNCTIONS ---
@st.cache_data
def load_data():
    """Loads BOTH Syllabus and PYQs"""
    topics = None
    pyqs_content = ""
    
    # 1. Load Syllabus
    if os.path.exists("data/syllabus.txt"):
        topics = load_text_file("data/syllabus.txt", "Syllabus")
    
    # 2. Load PYQs
    if os.path.exists("data/pyqs.txt"):
        with open("data/pyqs.txt", "r", encoding="utf-8") as f:
            pyqs_content = f.read()

    return topics, pyqs_content

@st.cache_data
def get_analysis(topics, pyqs_content):
    """Runs ALL AI tasks."""
    
    # 1. Relationships (Syllabus only)
    relations = analyze_deep_relations(topics)
    
    # 2. Importance (Syllabus + PYQs)
    importance = calculate_importance(topics, pyqs_content)
    
    node_metrics = {}
    total_time = 0
    
    # 3. Time & Difficulty
    for topic in topics:
        content = get_cached_content(topic)
        mins, diff, is_math = estimate_effort(content)
        
        node_metrics[topic] = {
            "time": mins, 
            "difficulty": diff,
            "is_math": is_math
        }
        total_time += mins
        
    return relations, importance, node_metrics, total_time

# --- MAIN UI ---
st.title("🧠 AI Exam Guiding System")

topics, pyqs_content = load_data()

if not topics:
    st.error("❌ Syllabus data not found. Please ensure 'data/syllabus.txt' exists.")
    st.stop()

if not pyqs_content:
    st.warning("⚠️ 'data/pyqs.txt' not found or empty. Importance scores may be inaccurate.")

relations, importance_scores, node_metrics, total_time = get_analysis(topics, pyqs_content)

# --- SIDEBAR ---
st.sidebar.header("🎛️ Controls")
# Defaulted slider to 0.15 so edges show up immediately
min_strength = st.sidebar.slider("Graph Complexity", 0.1, 1.0, 0.15, 0.05)
focus_topic = st.sidebar.selectbox("🔍 Focus Topic", ["None"] + topics)

# --- GRAPH GENERATION ---
G = nx.Graph()

for topic in topics:
    # --- SAFE DATA EXTRACTION (Prevents Crash) ---
    raw_data = importance_scores.get(topic, {"score": 0, "matches": []})
    
    # Handle old cache vs new data structure
    if isinstance(raw_data, (int, float)):
        score = raw_data
        data = {"score": raw_data, "matches": []}
    else:
        data = raw_data
        score = data.get("score", 0)

    meta = node_metrics.get(topic, {})
    
    # Priority Label
    priority_label = get_clean_priority_label(score)
    is_math = meta.get("is_math", False)
    
    # Visual Logic
    size = 15 + (score * 5)
    
    # Color Logic
    diff = meta.get("difficulty", "Unknown")
    color = "#00ff41" # Green
    if diff == "Moderate": color = "#ffff00" # Yellow
    if diff == "Hard": color = "#ff5733" # Red
    
    math_icon = "🧮 " if is_math else ""
    tooltip = f"{math_icon}{topic}\nPriority: {priority_label}\nDifficulty: {diff}\nTime: {meta['time']}m"
    
    G.add_node(topic, title=tooltip, label=topic, color=color, size=size)

# --- DRAW EDGES (This was missing!) ---
for link in relations:
    if link['score'] >= min_strength:
        G.add_edge(link['topic_a'], link['topic_b'], value=link['score'])

# Filter by Focus Topic
if focus_topic != "None" and focus_topic in G.nodes():
    neighbors = list(G.neighbors(focus_topic))
    G = G.subgraph(neighbors + [focus_topic])

# --- RENDER NETWORK ---
net = Network(height="500px", width="100%", bgcolor="#1e1e1e", font_color="white")
net.from_nx(G)
net.force_atlas_2based(gravity=-100, spring_length=200)
html_file = "graph_temp.html"
net.save_graph(html_file)

# --- DISPLAY OUTPUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Interactive Knowledge Graph")
    with open(html_file, 'r', encoding='utf-8') as f:
        components.html(f.read(), height=520)
    st.caption("🟢 Easy  🟡 Moderate  🔴 Hard | 🔵 Bigger Bubble = 🔥 Higher Priority")

with col2:
    st.subheader("📊 Strategic Study Table")
    
    hours = int(total_time/60)
    mins = total_time % 60
    st.info(f"⏱️ **Total Study Time:** {hours}h {mins}m")
    
    table_data = []
    for topic in topics:
        # Safe extraction for table
        raw_data = importance_scores.get(topic, {"score": 0})
        score = raw_data if isinstance(raw_data, (int, float)) else raw_data.get("score", 0)
        
        meta = node_metrics.get(topic, {})
        type_icon = "🧮 Math" if meta.get("is_math") else "📖 Theory"
        
        table_data.append({
            "Topic": topic,
            "Priority": get_clean_priority_label(score),
            "Type": type_icon,
            "Difficulty": meta.get("difficulty", "-"),
            "Time": meta.get("time", 0),
            "Raw_Score": score 
        })
    
    df = pd.DataFrame(table_data)
    
    if not df.empty:
        df = df.sort_values(by=["Raw_Score", "Time"], ascending=[False, False])
        display_df = df.drop(columns=["Raw_Score"])
        
        st.dataframe(
            display_df, 
            hide_index=True, 
            column_config={
                "Priority": st.column_config.TextColumn("Priority"),
                "Time": st.column_config.NumberColumn("Mins", format="%d m"),
                "Type": st.column_config.TextColumn("Type", width="small")
            }
        )

# --- SIDEBAR DETAILS ---
if focus_topic != "None":
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"📜 PYQs for: {focus_topic}")
    
    # Safe extraction for sidebar
    raw_data = importance_scores.get(focus_topic, {})
    # If old cache (float), we have no questions. If new dict, we do.
    questions = []
    if isinstance(raw_data, dict):
        questions = raw_data.get("matches", [])
    
    if questions:
        for q in questions:
            st.sidebar.info(f"❓ {q}")
    else:
        st.sidebar.caption("No direct matches found in PYQs.")