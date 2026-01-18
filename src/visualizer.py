import networkx as nx
from pyvis.network import Network
from deep_relations import analyze_deep_relations
from loader import load_text_file
import random

def create_knowledge_graph():
    syllabus_path = "data/syllabus.txt"
    topics = load_text_file(syllabus_path, "Syllabus")
    if not topics: return

    # 1. Get Relations
    print("🚀 Retrieving Relations...")
    relations = analyze_deep_relations(topics)
    
    # 2. Create NetworkX Graph (for calculations)
    G = nx.Graph()
    for link in relations:
        if link['score'] > 0.40: # STRICTER THRESHOLD for cleaner graph
            G.add_edge(link['topic_a'], link['topic_b'], weight=link['score'])

    # 3. Detect Communities (The "Coloring" Magic)
    # This finds groups of tightly connected topics
    print("🎨 Detecting Topic Clusters...")
    try:
        communities = nx.community.greedy_modularity_communities(G)
    except:
        # Fallback if graph is empty
        communities = []

    # Assign a unique color to each cluster
    # Colors: Red, Blue, Green, Orange, Purple, Teal, Pink
    colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#33FFF5', '#F5FF33', '#A133FF']
    topic_colors = {}
    
    for idx, community in enumerate(communities):
        # Cycle through colors if we have too many groups
        color = colors[idx % len(colors)]
        for node in community:
            topic_colors[node] = color

    # 4. Build PyVis Graph
    net = Network(height="750px", width="100%", bgcolor="#1a1a1a", font_color="white", select_menu=True)
    
    # PHYSICS: Make it spread out!
    net.force_atlas_2based(gravity=-100, central_gravity=0.01, spring_length=200, spring_strength=0.05)

    # Add Nodes with their Community Colors
    for node in G.nodes():
        # Get color (default to white if not in a main cluster)
        color = topic_colors.get(node, "#ffffff")
        
        # Shorten label for display
        label = node[:15] + ".." if len(node) > 15 else node
        
        # Add detailed tooltip
        net.add_node(node, label=label, title=node, color=color, size=25)

    # Add Edges
    for src, dst, data in G.edges(data=True):
        weight = data['weight']
        # Thinner lines, slightly transparent
        net.add_edge(src, dst, value=weight*3, color="#555555", title=f"Match: {weight:.2f}")

    # 5. Save and Options
    # Add buttons so you can play with physics in the browser
    net.show_buttons(filter_=['physics'])
    
    output_file = "knowledge_graph.html"
    net.save_graph(output_file)
    print(f"✅ Clustered Graph saved to '{output_file}'. Check out the colors!")

if __name__ == "__main__":
    create_knowledge_graph()