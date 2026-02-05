import streamlit as st
import graphviz
import uuid

# --- PAGE CONFIG ---
st.set_page_config(page_title="Advanced Event Tree", layout="wide")

# --- SESSION STATE INITIALIZATION ---
# This acts as the "database" for the current session
if 'tree_nodes' not in st.session_state:
    # Initialize with the Root Node (Initiating Event)
    root_id = str(uuid.uuid4())[:8]
    st.session_state.tree_nodes = {
        root_id: {
            "name": "Fire Ignition",
            "type": "root",
            "prob": 1.0,  # Probability of this specific event happening (1.0 for root)
            "path_prob": 1.0,  # Cumulative probability reaching this point
            "parent_id": None,
            "branch": None  # "Yes" or "No" connection from parent
        }
    }

if 'tree_edges' not in st.session_state:
    st.session_state.tree_edges = []  # List of tuples (parent_id, child_id, label)


# --- HELPER FUNCTIONS ---
def add_node(parent_id, name, success_prob, is_outcome=False):
    new_id = str(uuid.uuid4())[:8]
    parent = st.session_state.tree_nodes[parent_id]

    # Calculate probabilities
    # We create TWO nodes logically when adding a barrier: The Success path and the Failure path
    # But for the UI, we usually add one barrier at a time.
    # To keep it flexible, we will just add the node the user requested.

    st.session_state.tree_nodes[new_id] = {
        "name": name,
        "type": "outcome" if is_outcome else "event",
        "prob": success_prob,
        "parent_id": parent_id,
    }
    return new_id


def reset_tree():
    st.session_state.tree_nodes = {}
    st.session_state.tree_edges = []
    # Re-init root
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
st.sidebar.title("🌳 Tree Builder")

# 1. Edit Root Name
root_node = next(n for n in st.session_state.tree_nodes.values() if n['type'] == 'root')
new_root_name = st.sidebar.text_input("Initiating Event Name", root_node['name'])
if new_root_name != root_node['name']:
    # Update root name
    for k, v in st.session_state.tree_nodes.items():
        if v['type'] == 'root':
            st.session_state.tree_nodes[k]['name'] = new_root_name

st.sidebar.markdown("---")

# 2. Add New Branch/Event
st.sidebar.subheader("Add New Branch")

# Create list of potential parents (names + IDs) for the dropdown
node_options = {k: f"{v['name']} ({k})" for k, v in st.session_state.tree_nodes.items() if v['type'] != 'outcome'}
parent_id = st.sidebar.selectbox("Attach to Parent Node:", options=list(node_options.keys()),
                                 format_func=lambda x: node_options[x])

branch_type = st.sidebar.radio("Connect via which path?", ["Success (Yes)", "Failure (No)"])
node_type = st.sidebar.radio("Is this a new Barrier or Final Outcome?", ["New Barrier", "Final Outcome"])

new_node_name = st.sidebar.text_input("Name of Event/Outcome", "Sprinkler Activation")

if node_type == "New Barrier":
    success_prob = st.sidebar.slider("Probability of Success", 0.0, 1.0, 0.9, step=0.01)
else:
    success_prob = 1.0  # Outcomes don't have their own success probability, they are endpoints

if st.sidebar.button("Add to Tree"):
    # 1. Create the new Node ID
    new_id = str(uuid.uuid4())[:8]

    # 2. Get Parent Data to calculate cumulative probability
    parent = st.session_state.tree_nodes[parent_id]

    # Calculate edge probability (Probability of taking this branch)
    # If parent is a Barrier, it has a "prob" of success.
    # If we take "Yes" branch, edge_prob = parent['prob']
    # If we take "No" branch, edge_prob = 1 - parent['prob']
    # NOTE: Root node always passes 1.0

    if parent['type'] == 'root':
        edge_prob = 1.0
    else:
        # If we are branching off a previous barrier, we need to know THAT barrier's success prob
        # For this logic, we assume the user enters the probability of THIS new node working.
        # The probability of *reaching* this node is determined by the connection.

        # Correction for logical flow:
        # In this builder, 'prob' stored in a node is "Probability this node SUCCEEDS".
        # The connection determines if we are on the failure or success path of the PARENT.
        if branch_type == "Success (Yes)":
            edge_prob = parent['prob']
        else:
            edge_prob = 1.0 - parent['prob']

    # Cumulative Path Probability = Parent's Path Prob * Edge Prob
    new_path_prob = parent['path_prob'] * edge_prob

    # 3. Store Node
    st.session_state.tree_nodes[new_id] = {
        "name": new_node_name,
        "type": "outcome" if node_type == "Final Outcome" else "event",
        "prob": success_prob if node_type == "New Barrier" else 0,  # Prob of THIS barrier succeeding
        "path_prob": new_path_prob,
        "parent_id": parent_id,
        "branch": branch_type
    }

    # 4. Store Edge (for Graphviz)
    edge_label = f"Yes\n({parent['prob']:.2f})" if branch_type == "Success (Yes)" and parent['type'] != 'root' else \
        f"No\n({1.0 - parent['prob']:.2f})" if branch_type == "Failure (No)" and parent['type'] != 'root' else ""

    st.session_state.tree_edges.append({
        "source": parent_id,
        "target": new_id,
        "label": edge_label,
        "color": "#2F855A" if branch_type == "Success (Yes)" else "#C53030"
    })
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚠️ Reset Tree"):
    reset_tree()
    st.rerun()

# --- MAIN AREA: VISUALIZATION ---
st.title("🛡️ Advanced Event Tree Builder")

# Build Graphviz Object
dot = graphviz.Digraph()
dot.attr(rankdir='LR', splines='ortho')
dot.attr('node', fontname='Helvetica')

# Draw Nodes
for node_id, node in st.session_state.tree_nodes.items():

    # Label construction
    if node['type'] == 'root':
        label = f"{node['name']}\n(Start)"
        shape = 'ellipse'
        color = '#2B6CB0'  # Blue
        fill = '#EBF8FF'
    elif node['type'] == 'outcome':
        label = f"{node['name']}\nPath Prob: {node['path_prob']:.4f}"
        shape = 'note'
        # Color outcome based on branch
        color = '#2F855A' if node['branch'] == "Success (Yes)" else '#C53030'
        fill = '#F0FFF4' if node['branch'] == "Success (Yes)" else '#FFF5F5'
    else:
        # Barrier
        label = f"{node['name']}\n(Success Prob: {node['prob']:.2f})"
        shape = 'box'
        color = '#4A5568'
        fill = 'white'

    dot.node(node_id, label, shape=shape, color=color, style='filled', fillcolor=fill)

# Draw Edges
for edge in st.session_state.tree_edges:
    dot.edge(edge['source'], edge['target'], label=edge['label'], color=edge['color'], fontcolor=edge['color'])

st.graphviz_chart(dot)

# --- DATA TABLE ---
st.markdown("### 📋 Node Data")
st.write(st.session_state.tree_nodes)