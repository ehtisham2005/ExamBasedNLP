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
    """
    Uses Symbols instead of Colors to prevent UI confusion.
    """
    if score > 2.5: return "🔥🔥🔥 High"  # Fire = Importance
    if score > 1.0: return "🔥🔥 Med"
    return "🔹 Low"

# --- CACHED FUNCTIONS ---
@st.cache_data
def load_data():
    if os.path.exists("data/syllabus.txt"):
        return load_text_file("data/syllabus.txt", "Syllabus")
    return None

@st.cache_data
def get_analysis(topics):
    """Runs ALL AI tasks: Relations, Importance, and Time Estimation"""
    relations = analyze_deep_relations(topics)
    importance = calculate_importance(topics)
    
    node_metrics = {}
    total_time = 0
    
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

topics = load_data()
if not topics:
    st.error("❌ Data not found. Please ensure 'data/syllabus.txt' exists.")
    st.stop()

relations, importance_scores, node_metrics, total_time = get_analysis(topics)

# --- SIDEBAR ---
st.sidebar.header("🎛️ Controls")
min_strength = st.sidebar.slider("Graph Complexity", 0.1, 1.0, 0.40, 0.05)
focus_topic = st.sidebar.selectbox("🔍 Focus Topic", ["None"] + topics)

# --- GRAPH GENERATION ---
G = nx.Graph()

for topic in topics:
    score = importance_scores.get(topic, 0)
    meta = node_metrics.get(topic, {})
    
    # Use the NEW icon system
    priority_label = get_clean_priority_label(score)
    is_math = meta.get("is_math", False)
    
    # Visual Logic:
    size = 15 + (score * 5)
    
    # Color = Difficulty (Strictly Red/Yellow/Green)
    diff = meta.get("difficulty", "Unknown")
    color = "#00ff41" # Green (Easy)
    if diff == "Moderate": color = "#ffff00" # Yellow
    if diff == "Hard": color = "#ff5733" # Red
    
    # Tooltip
    math_icon = "🧮 " if is_math else ""
    tooltip = f"{math_icon}{topic}\nPriority: {priority_label}\nDifficulty: {diff}\nTime: {meta['time']}m"
    
    G.add_node(topic, title=tooltip, label=topic, color=color, size=size)

for link in relations:
    if link['score'] >= min_strength:
        G.add_edge(link['topic_a'], link['topic_b'], value=link['score'])

if focus_topic != "None" and focus_topic in G.nodes():
    neighbors = list(G.neighbors(focus_topic))
    G = G.subgraph(neighbors + [focus_topic])

net = Network(height="500px", width="100%", bgcolor="#1e1e1e", font_color="white")
net.from_nx(G)
net.force_atlas_2based(gravity=-100, spring_length=200)
html_file = "graph_temp.html"
net.save_graph(html_file)

# --- LAYOUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Interactive Knowledge Graph")
    with open(html_file, 'r', encoding='utf-8') as f:
        components.html(f.read(), height=520)
    # Clear Legend
    st.caption("🟢 Easy  🟡 Moderate  🔴 Hard | 🔵 Bigger Bubble = 🔥 Higher Priority")

with col2:
    st.subheader("📊 Strategic Study Table")
    
    hours = int(total_time/60)
    mins = total_time % 60
    st.info(f"⏱️ **Total Study Time:** {hours}h {mins}m")
    
    table_data = []
    for topic in topics:
        score = importance_scores.get(topic, 0)
        meta = node_metrics.get(topic, {})
        type_icon = "🧮 Math" if meta.get("is_math") else "📖 Theory"
        
        table_data.append({
            "Topic": topic,
            "Priority": get_clean_priority_label(score), # New Icons
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
            # REMOVED: use_container_width=True (Fixes your error)
            column_config={
                "Priority": st.column_config.TextColumn("Priority"),
                "Time": st.column_config.NumberColumn("Mins", format="%d m"),
                "Type": st.column_config.TextColumn("Type", width="small")
            }
        )