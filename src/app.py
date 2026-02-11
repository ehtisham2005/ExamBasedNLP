import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import pandas as pd
import warnings
import os
import re
from dotenv import load_dotenv 
from groq import Groq

# --- CUSTOM MODULE IMPORTS ---
# Ensure these files exist in your directory
from loader import load_text_file
from deep_relations import analyze_deep_relations
from fetcher import fetch_topic_content 
from metrics import estimate_effort
from analyzer import calculate_importance
from parser import ExamParser

# --- CONFIGURATION ---
load_dotenv()
warnings.filterwarnings("ignore", category=ResourceWarning)
st.set_page_config(
    page_title="Exam Guide AI Pro", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1E1E1E;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B;
        color: white;
    }
    .stChatMessage {
        background-color: #262730; 
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'history' not in st.session_state: st.session_state['history'] = [] 
if 'force_refresh' not in st.session_state: st.session_state['force_refresh'] = False

# --- HELPER FUNCTIONS ---
def match_pyqs_to_topic(topic, pyqs_data):
    if not pyqs_data: return []
    lines = re.split(r'\n(?=\d+\.)|\n', pyqs_data) if isinstance(pyqs_data, str) else pyqs_data
    topic_words = set(re.findall(r'\w+', topic.lower()))
    relevant_questions = []
    
    for line in lines:
        line_clean = line.strip()
        if len(line_clean) < 10: continue 
        line_lower = line_clean.lower()
        if topic.lower() in line_lower:
            relevant_questions.append(line_clean)
        else:
            line_words = set(re.findall(r'\w+', line_lower))
            significant_topic_words = {w for w in topic_words if len(w) > 3}
            if significant_topic_words and significant_topic_words.issubset(line_words):
                relevant_questions.append(line_clean)
    return list(set(relevant_questions)) 

def get_groq_generator(stream):
    """Yields clean string content from the Groq stream object"""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

@st.cache_data(show_spinner=False)
def process_syllabus_data(refresh_trigger):
    try:
        parser = ExamParser(syllabus_path="data/syllabus.txt", pyqs_path="data/pyqs.txt")
        topics = parser.parse_syllabus()
        pyqs_content = parser.parse_pyqs()

        if not topics: return None, None, None, None, None, 0

        relations = analyze_deep_relations(topics)
        importance = calculate_importance(topics, pyqs_content)
        
        node_metrics = {}
        total_time = 0
        
        for topic in topics:
            content = fetch_topic_content(topic)
            if not content or len(content) < 50:
                content = f"Analysis of {topic} requires understanding of core principles."
            
            mins, diff, is_math = estimate_effort(content)
            node_metrics[topic] = {
                "time": mins, "difficulty": diff, 
                "is_math": is_math, "content_snippet": content[:500]
            }
            total_time += mins
            
        return topics, pyqs_content, relations, importance, node_metrics, total_time
    except Exception as e:
        st.error(f"Data Processing Error: {e}")
        return None, None, None, None, None, 0

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or st.session_state.get("USER_GROQ_KEY")
    return Groq(api_key=api_key) if api_key else None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=50)
    st.title("Exam Guide AI")
    st.markdown("---")
    
    if not os.getenv("GROQ_API_KEY") and 'USER_GROQ_KEY' not in st.session_state:
        st.warning("⚠️ API Key Required")
        user_key = st.text_input("Enter Groq API Key", type="password")
        if user_key:
            st.session_state['USER_GROQ_KEY'] = user_key
            st.rerun()
    else:
        st.success("🟢 System Online")

    st.markdown("### ⚙️ Graph Controls")
    min_strength = st.slider("Min Edge Strength", 0.0, 1.0, 0.35, 0.05)
    physics = st.toggle("Enable Physics", value=True)
    
    st.markdown("---")
    if st.button("🔄 Refresh Analysis"):
        st.cache_data.clear()
        st.session_state['force_refresh'] = not st.session_state['force_refresh']
        st.rerun()
    if st.button("🗑️ Clear Chat History"):
        st.session_state['history'] = []
        st.rerun()

# --- MAIN LOGIC ---
with st.spinner("🚀 Analyzing Syllabus..."):
    topics, pyqs_raw, relations, importance_scores, node_metrics, total_time = process_syllabus_data(st.session_state['force_refresh'])

if not topics:
    st.error("❌ Failed to load data. Please check `data/syllabus.txt`.")
    st.stop()

# Prepare DataFrame
df_data = []
for topic in topics:
    raw_score = importance_scores.get(topic, {"score": 0})
    score = raw_score.get("score", 0) if isinstance(raw_score, dict) else 0
    meta = node_metrics.get(topic, {})
    
    df_data.append({
        "Topic": topic,
        "Relevance": score,
        "Time": meta.get("time", 15),
        "Difficulty": meta.get("difficulty", "Moderate"),
        "Type": "🧮 Math" if meta.get("is_math") else "📖 Theory"
    })

df = pd.DataFrame(df_data)

# Priority Logic
high_q = df['Relevance'].quantile(0.85)
med_q = df['Relevance'].quantile(0.50)
df['Priority'] = df['Relevance'].apply(lambda x: "🔴 HIGH" if x >= high_q else ("🟡 MED" if x >= med_q else "🟢 LOW"))

# --- DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Topics", len(topics))
with col2: st.metric("Est. Time", f"{int(total_time/60)}h {total_time%60}m")
with col3: st.metric("Critical Topics", len(df[df['Priority'] == "🔴 HIGH"]), delta="Focus Here", delta_color="inverse")
with col4: st.metric("Math Heavy", len(df[df['Type'] == "🧮 Math"]))

st.markdown("---")
tab_graph, tab_study, tab_tutor, tab_pyq = st.tabs(["📊 Knowledge Graph", "📚 Topic Explorer", "🤖 AI Tutor", "📄 PYQ Bank"])

# --- TAB 1: KNOWLEDGE GRAPH ---
with tab_graph:
    # 1. Initialize Network
    net = Network(height="600px", width="100%", bgcolor="#1E1E1E", font_color="white", cdn_resources='in_line')
    
    # 2. Add Nodes
    for _, row in df.iterrows():
        if row['Priority'] == "🔴 HIGH": color = "#ff4b4b"
        elif row['Priority'] == "🟡 MED": color = "#ffa500"
        else: color = "#00d4ff" 
        
        size = 20 + (row['Relevance'] * 15)
        tooltip = f"Topic: {row['Topic']}\nPriority: {row['Priority']}\nDiff: {row['Difficulty']}"
        
        net.add_node(row['Topic'], label=row['Topic'], color=color, size=size, title=tooltip, 
                     borderWidth=2, font={'size': 14, 'color': 'white'})

    # 3. Add Edges
    for link in relations:
        if link['score'] >= min_strength:
            width = 1 + (link['score'] * 4)
            net.add_edge(link['topic_a'], link['topic_b'], value=link['score'], width=width, 
                         title=f"Strength: {link['score']:.2f}", 
                         color={'color': '#666666', 'opacity': 0.6})

    # 4. Physics - Barnes Hut is more stable for visibility than ForceAtlas2Based
    net.barnes_hut(gravity=-2500, central_gravity=0.4, spring_length=125, spring_strength=0.05, damping=0.09, overlap=0)
    
    if not physics: net.toggle_physics(False)
        
    # 5. RENDER FIX
    path = "graph_viz.html"
    try:
        html_data = net.generate_html()
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_data)
        components.html(html_data, height=620, scrolling=False)
    except Exception as e:
        st.error(f"Error rendering graph: {e}")

    # 6. TABLE BELOW GRAPH
    st.markdown("### 📋 Topic Details")
    filter_pri = st.multiselect("Filter Priority", ["🔴 HIGH", "🟡 MED", "🟢 LOW"], default=["🔴 HIGH", "🟡 MED", "🟢 LOW"])
    filtered_df = df[df['Priority'].isin(filter_pri)].sort_values(by="Relevance", ascending=False)
    
    st.dataframe(
        filtered_df[['Topic', 'Priority', 'Difficulty', 'Type', 'Time']],
        hide_index=True, width='stretch',
        column_config={
            "Topic": st.column_config.TextColumn("Topic", width="medium"),
            "Time": st.column_config.ProgressColumn("Time (m)", format="%d", min_value=0, max_value=120),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
        },
        height=400
    )

# --- TAB 2: EXPLORER ---
with tab_study:
    st.info("Select a topic to view context & specific PYQs.")
    col_select, col_details = st.columns([1, 2])
    with col_select:
        selected_study_topic = st.radio("Select Topic:", sorted(df['Topic'].unique()), index=0, key="study_radio")
    with col_details:
        if selected_study_topic:
            row = df[df['Topic'] == selected_study_topic].iloc[0]
            st.title(selected_study_topic)
            b1, b2, b3 = st.columns(3)
            b1.metric("Type", row['Type'])
            b2.metric("Difficulty", row['Difficulty'])
            b3.metric("Est. Time", f"{row['Time']} mins")
            st.markdown("---")
            with st.expander("📖 Quick Context", expanded=True):
                st.write(node_metrics[selected_study_topic]['content_snippet'] + "...")
            st.subheader("📝 Relevant PYQs")
            matches = match_pyqs_to_topic(selected_study_topic, pyqs_raw)
            if matches:
                for idx, q in enumerate(matches, 1): st.success(f"**Q{idx}:** {q}")
            else:
                st.warning("No direct matches in PYQs.")

# --- TAB 3: TUTOR ---
with tab_tutor:
    st.subheader("💬 Chat with your Syllabus")
    c_ctrl, c_box = st.columns([1, 3])
    with c_ctrl:
        chat_topic = st.selectbox("Focus Conversation On:", ["General"] + list(df['Topic']))
    with c_box:
        # Render history
        for msg in st.session_state['history']:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input("Ask a doubt..."):
            st.session_state['history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            client = get_groq_client()
            if not client: st.error("API Key Required"); st.stop()
            
            ctx = ""
            if chat_topic != "General":
                ctx = fetch_topic_content(chat_topic)
                pyqs = match_pyqs_to_topic(chat_topic, pyqs_raw)
                if pyqs: ctx += f"\nPYQS:\n" + "\n".join(pyqs)
            
            sys_prompt = f"Expert Tutor. Topic: {chat_topic}. Context: {ctx[:4000]}. Be concise. Use Markdown."
            
            with st.chat_message("assistant"):
                try:
                    stream = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                        stream=True, max_tokens=1024
                    )
                    # FIX: Use the generator wrapper
                    resp = st.write_stream(get_groq_generator(stream))
                    st.session_state['history'].append({"role": "assistant", "content": resp})
                except Exception as e: st.error(f"Error: {e}")

# --- TAB 4: PYQ BANK (NEW) ---
with tab_pyq:
    st.subheader("📄 All Past Year Questions")
    
    if isinstance(pyqs_raw, str):
        pyqs_list = re.split(r'\n(?=\d+\.)|\n', pyqs_raw)
    elif isinstance(pyqs_raw, list):
        pyqs_list = pyqs_raw
    else:
        pyqs_list = []
        
    # Search Filter
    search_query = st.text_input("🔍 Search Questions", placeholder="Type keywords (e.g., 'Agile', 'Testing')...")
    
    filtered_pyqs = [q for q in pyqs_list if len(q) > 10]
    if search_query:
        filtered_pyqs = [q for q in filtered_pyqs if search_query.lower() in q.lower()]
        
    st.write(f"Showing {len(filtered_pyqs)} questions:")
    for i, q in enumerate(filtered_pyqs, 1):
        st.info(f"**{i}.** {q.strip()}")

st.markdown("---")
st.markdown("<center>Calculated with ❤️ using Graph Theory & LLMs</center>", unsafe_allow_html=True)