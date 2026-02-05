import streamlit as st
import graphviz
import uuid

# --- PAGE CONFIG ---
st.set_page_config(page_title="Event Tree Analysis", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if 'tree_nodes' not in st.session_state:
    root_id = str(uuid.uuid4())[:8]
    st.session_state.tree_nodes = {
        root_id: {
            "name": "Fire Ignition",
            "type": "root",
            "prob": 1.0,
            "path_prob": 1.0,
            "parent_id": None,
            "branch": None
        }
    }

if 'tree_edges' not in st.session_state:
    st.session_state.tree_edges = []


# --- HELPER FUNCTIONS ---
def reset_tree():
    st.session_state.tree_nodes = {}
    st.session_state.tree_edges = []
    root_id = str(uuid.uuid4())[:8]
    st.session_state.tree_nodes[root_id] = {
        "name": "Fire Ignition",
        "type": "root",
        "prob": 1.0,
        "path_prob": 1.0,
        "parent_id": None,
        "branch": None
    }


# --- SIDEBAR: CONTROLS ---
st.sidebar.header("Configuration")

# 1. Edit Root Name
root_node = next(n for n in st.session_state.tree_nodes.values() if n['type'] == 'root')
new_root_name = st.sidebar.text_input("Initiating Event Name", root_node['name'])
if new_root_name != root_node['name']:
    for k, v in st.session_state.tree_nodes.items():
        if v['type'] == 'root':
            st.session_state.tree_nodes[k]['name'] = new_root_name

st.sidebar.markdown("---")

# 2. Add New Branch/Event
st.sidebar.subheader("Add New Event")

# Create options for dropdown
node_options = {k: f"{v['name']}" for k, v in st.session_state.tree_nodes.items() if v['type'] != 'outcome'}
parent_id = st.sidebar.selectbox("Attach to Parent Node:", options=list(node_options.keys()),
                                 format_func=lambda x: node_options[x])

branch_type = st.sidebar.radio("Connect via which path?", ["Success (Yes)", "Failure (No)"])
node_type = st.sidebar.radio("Is this a new Barrier or Final Outcome?", ["New Barrier", "Final Outcome"])

new_node_name = st.sidebar.text_input("Name of Event/Outcome", "Sprinkler Activation")

if node_type == "New Barrier":
    success_prob = st.sidebar.slider("Probability of Success", 0.0, 1.0, 0.9, step=0.01)
else:
    success_prob = 1.0

if st.sidebar.button("Add to Tree"):
    new_id = str(uuid.uuid4())[:8]
    parent = st.session_state.tree_nodes[parent_id]

    # Calculate Probabilities
    if parent['type'] == 'root':
        edge_prob = 1.0
    else:
        if branch_type == "Success (Yes)":
            edge_prob = parent['prob']
        else:
            edge_prob = 1.0 - parent['prob']

    new_path_prob = parent['path_prob'] * edge_prob

    # Store Node
    st.session_state.tree_nodes[new_id] = {
        "name": new_node_name,
        "type": "outcome" if node_type == "Final Outcome" else "event",
        "prob": success_prob if node_type == "New Barrier" else 0,
        "path_prob": new_path_prob,
        "parent_id": parent_id,
        "branch": branch_type
    }

    # Store Edge
    edge_label = f"Yes\n({parent['prob']:.2f})" if branch_type == "Success (Yes)" and parent['type'] != 'root' else \
        f"No\n({1.0 - parent['prob']:.2f})" if branch_type == "Failure (No)" and parent['type'] != 'root' else ""

    st.session_state.tree_edges.append({
        "source": parent_id,
        "target": new_id,
        "label": edge_label,
        "color": "black"
    })
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Reset Tree"):
    reset_tree()
    st.rerun()

# --- MAIN AREA: VISUALIZATION ---
st.title("Event Tree Analysis")

# Build Graphviz Object
dot = graphviz.Digraph()
dot.attr(rankdir='LR', splines='ortho')
dot.attr('node', fontname='Arial', fontsize='12')
dot.attr('edge', fontname='Arial', fontsize='10')

# Draw Nodes
for node_id, node in st.session_state.tree_nodes.items():
    if node['type'] == 'root':
        label = f"{node['name']}\n(Start)"
        shape = 'box'
        style = 'rounded,filled'
        fillcolor = '#E3F2FD'  # Light Blue
        color = '#1565C0'
    elif node['type'] == 'outcome':
        label = f"{node['name']}\nProb: {node['path_prob']:.4f}"
        shape = 'note'
        style = 'filled'
        fillcolor = '#F5F5F5'  # Light Gray
        color = '#424242'
    else:
        label = f"{node['name']}\n(P(Success): {node['prob']:.2f})"
        shape = 'box'
        style = 'filled'
        fillcolor = '#FFFFFF'  # White
        color = '#000000'

    dot.node(node_id, label, shape=shape, color=color, style=style, fillcolor=fillcolor)

# Draw Edges
for edge in st.session_state.tree_edges:
    dot.edge(edge['source'], edge['target'], label=edge['label'], color='#555555', fontcolor='#333333')

# Render
st.graphviz_chart(dot)

# Placeholder if empty
if len(st.session_state.tree_nodes) == 1:
    st.info("The tree is currently empty. Use the sidebar to add your first barrier (e.g., 'Smoke Detector').")

# --- DATA TABLE (Hidden by default) ---
with st.expander("Show Calculation Data"):
    st.write(st.session_state.tree_nodes)