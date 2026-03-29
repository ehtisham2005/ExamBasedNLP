import streamlit as st
import os
import re
import warnings
import networkx as nx
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components
from dotenv import load_dotenv 
from groq import Groq

# --- CUSTOM MODULE IMPORTS ---
from parser import ExamParser
from deep_relations import analyze_deep_relations
from fetcher import fetch_topic_content 
from metrics import estimate_effort
from analyzer import calculate_importance

# --- CONFIGURATION ---
load_dotenv()
warnings.filterwarnings("ignore", category=ResourceWarning)
st.set_page_config(
    page_title="Universal Exam Guide AI Pro", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE ---
if 'history' not in st.session_state: st.session_state['history'] = [] 
if 'force_refresh' not in st.session_state: st.session_state['force_refresh'] = False

# --- HELPER FUNCTIONS ---

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or st.session_state.get("USER_GROQ_KEY")
    return Groq(api_key=api_key) if api_key else None

def get_groq_generator(stream):
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content

def match_pyqs_to_topic(topic, pyqs_list):
    """Fuzzy matching for questions in the Explorer tab"""
    if not pyqs_list: return []
    relevant_questions = []
    topic_words = {w for w in re.findall(r'\w+', topic.lower()) if len(w) > 3}
    
    for q in pyqs_list:
        q_lower = q.lower()
        if topic.lower() in q_lower:
            relevant_questions.append(q)
            continue
        
        q_words = set(re.findall(r'\w+', q_lower))
        if topic_words and len(topic_words.intersection(q_words)) / len(topic_words) >= 0.7:
            relevant_questions.append(q)
                 
    return list(set(relevant_questions)) 

@st.cache_data(show_spinner=False)
def process_subject_data(syllabus_file, pyq_file, refresh_trigger):
    """Saves bytes to temp files and runs the universal parser for any subject"""
    try:
        with open("temp_syllabus.txt", "wb") as f:
            f.write(syllabus_file.getbuffer())
        with open("temp_pyqs.txt", "wb") as f:
            f.write(pyq_file.getbuffer())
        
        parser = ExamParser("temp_syllabus.txt", "temp_pyqs.txt")
        topics = parser.parse_syllabus()
        pyqs_list = parser.parse_pyqs()

        if not topics: return None, None, None, None, None, 0

        relations = analyze_deep_relations(topics)
        importance = calculate_importance(topics, pyqs_list)
        
        node_metrics = {}
        total_time = 0
        
        for topic in topics:
            content = fetch_topic_content(topic)
            if not content or len(content) < 50:
                content = f"Study material for {topic} focuses on fundamental concepts and applications."
            
            mins, diff, is_math = estimate_effort(content)
            node_metrics[topic] = {
                "time": mins, 
                "difficulty": diff, 
                "is_math": is_math, 
                "content_snippet": content[:500]
            }
            total_time += mins
            
        return topics, pyqs_list, relations, importance, node_metrics, total_time
    except Exception as e:
        st.error(f"Processing Error: {e}")
        return None, None, None, None, None, 0

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎓 Subject Config")
    st.markdown("---")
    
    # Dynamic File Uploaders
    u_syllabus = st.file_uploader("Upload Syllabus (.txt)", type="txt")
    u_pyqs = st.file_uploader("Upload PYQs (.txt)", type="txt")
    
    if not u_syllabus or not u_pyqs:
        st.info("Please upload both files to begin.")
        st.stop()

    st.markdown("---")
    if not os.getenv("GROQ_API_KEY") and 'USER_GROQ_KEY' not in st.session_state:
        user_key = st.text_input("Enter Groq API Key", type="password")
        if user_key:
            st.session_state['USER_GROQ_KEY'] = user_key
            st.rerun()
    
    st.markdown("### ⚙️ Visuals")
    min_strength = st.slider("Min Edge Strength", 0.0, 1.0, 0.35, 0.05)
    physics = st.toggle("Enable Physics", value=True)
    
    if st.button("🔄 Reset Analysis"):
        st.cache_data.clear()
        st.session_state['force_refresh'] = not st.session_state['force_refresh']
        st.rerun()

# --- MAIN LOGIC ---
with st.spinner("🚀 Analyzing Your Subject..."):
    topics, pyqs_list, relations, importance_scores, node_metrics, total_time = process_subject_data(
        u_syllabus, u_pyqs, st.session_state['force_refresh']
    )

# Prepare Dataframe with Percentile Priority
df_data = []
for topic in topics:
    raw_score = importance_scores.get(topic, {"score": 0})
    score = raw_score.get("score", 0) if isinstance(raw_score, dict) else 0
    meta = node_metrics.get(topic, {})
    df_data.append({
        "Topic": topic, "Relevance": score, "Time": meta.get("time", 15),
        "Difficulty": meta.get("difficulty", "Moderate"),
        "Type": "🧮 Math" if meta.get("is_math") else "📖 Theory"
    })

df = pd.DataFrame(df_data)
if not df.empty:
    df['Percentile'] = df['Relevance'].rank(pct=True)
    def assign_pri(pct):
        if pct >= 0.85: return "🔴 HIGH"
        return "🟡 MED" if pct >= 0.50 else "🟢 LOW"
    df['Priority'] = df['Percentile'].apply(assign_pri)

# --- DASHBOARD UI ---
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Topics", len(topics))
with col2: st.metric("Est. Prep Time", f"{int(total_time/60)}h {total_time%60}m")
with col3: st.metric("High Priority", len(df[df['Priority'] == "🔴 HIGH"]))
with col4: st.metric("Calculation Heavy", len(df[df['Type'] == "🧮 Math"]))

tab_graph, tab_study, tab_tutor, tab_pyq = st.tabs(["📊 Knowledge Graph", "📚 Explorer", "🤖 AI Tutor", "📄 Question Bank"])

with tab_graph:
    net = Network(height="600px", width="100%", bgcolor="#1E1E1E", font_color="white")
    for _, row in df.iterrows():
        color = "#ff4b4b" if row['Priority'] == "🔴 HIGH" else "#ffa500" if row['Priority'] == "🟡 MED" else "#00d4ff"
        size = 20 + (row['Percentile'] * 15)
        net.add_node(row['Topic'], label=row['Topic'], color=color, size=size, title=f"Priority: {row['Priority']}")
    
    for link in relations:
        if link['score'] >= min_strength:
            net.add_edge(link['topic_a'], link['topic_b'], value=link['score'], color="#666666")
    
    net.toggle_physics(physics)
    net.save_graph("graph_viz.html")
    components.html(open("graph_viz.html", "r").read(), height=620)

with tab_study:
    col_sel, col_det = st.columns([1, 2])
    with col_sel:
        selected_topic = st.radio("Pick a Topic:", sorted(df['Topic'].unique()))
    with col_det:
        row = df[df['Topic'] == selected_topic].iloc[0]
        st.title(selected_topic)
        st.write(f"**Type:** {row['Type']} | **Difficulty:** {row['Difficulty']} | **Mins:** {row['Time']}")
        st.markdown("---")
        st.write(node_metrics[selected_topic]['content_snippet'] + "...")
        st.subheader("Related Exam Questions")
        matches = match_pyqs_to_topic(selected_topic, pyqs_list)
        for q in matches: st.info(q)

with tab_tutor:
    chat_topic = st.selectbox("Topic Focus:", ["General"] + list(df['Topic']))
    for msg in st.session_state['history']:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Ask a question..."):
        st.session_state['history'].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        client = get_groq_client()
        if client:
            ctx = node_metrics.get(chat_topic, {}).get("content_snippet", "")
            sys_msg = f"Expert Tutor for {chat_topic}. Context: {ctx}. Use Markdown."
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model="llama3-70b-8192", 
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state['history'],
                    stream=True
                )
                resp = st.write_stream(get_groq_generator(stream))
                st.session_state['history'].append({"role": "assistant", "content": resp})

with tab_pyq:
    search = st.text_input("🔍 Search Bank")
    for i, q in enumerate([q for q in pyqs_list if search.lower() in q.lower()], 1):
        st.info(f"**{i}.** {q}")