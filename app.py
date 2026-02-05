import streamlit as st
import graphviz
import uuid
from collections import deque

# --- PAGE CONFIG ---
st.set_page_config(page_title="Event Tree Manager", layout="wide")

# --- SESSION STATE ---
if 'tree_nodes' not in st.session_state:
    root_id = str(uuid.uuid4())[:8]
    st.session_state.tree_nodes = {
        root_id: {
            "name": "Fire Ignition",
            "type": "root",
            "prob": 1.0,  # Root probability (always 1)
            "path_prob": 1.0,  # Cumulative probability
            "parent_id": None,
            "branch": None  # "Success (Yes)" or "Failure (No)"
        }
    }


# --- ENGINE: LOGIC & MATH ---
def recalculate_tree():
    """
    Traverses the tree from Root down.
    1. Updates path probabilities based on parent values.
    2. Ensures mathematical consistency after any edit.
    """
    nodes = st.session_state.tree_nodes

    # Find Root
    root_id = next(nid for nid, n in nodes.items() if n['type'] == 'root')

    # BFS Traversal
    queue = deque([root_id])

    while queue:
        current_id = queue.popleft()
        current_node = nodes[current_id]

        # Find all children of this node
        children = [nid for nid, n in nodes.items() if n['parent_id'] == current_id]

        for child_id in children:
            child = nodes[child_id]

            # Calculate Edge Probability
            # If parent is Root, connection is 1.0.
            # Otherwise, it depends on if we are on the Success or Failure branch.
            if current_node['type'] == 'root':
                edge_prob = 1.0
            else:
                if child['branch'] == "Success (Yes)":
                    edge_prob = current_node['prob']
                else:
                    edge_prob = 1.0 - current_node['prob']

            # Update Child's Cumulative Path Probability
            child['path_prob'] = current_node['path_prob'] * edge_prob

            # Update the node in state
            nodes[child_id] = child

            # Add to queue to process ITS children next
            queue.append(child_id)


def get_subtree_ids(node_id):
    """Returns a list of all node IDs that are descendants of the given node."""
    ids_to_remove = []
    queue = deque([node_id])

    while queue:
        curr = queue.popleft()
        ids_to_remove.append(curr)
        # Find children
        children = [nid for nid, n in st.session_state.tree_nodes.items() if n['parent_id'] == curr]
        queue.extend(children)

    return ids_to_remove


def delete_node(node_id):
    """Deletes a node and ALL its children (Cascade Delete)."""
    targets = get_subtree_ids(node_id)
    for t in targets:
        del st.session_state.tree_nodes[t]
    recalculate_tree()


# --- SIDEBAR: MANAGER ---
st.sidebar.title("🛠️ Tree Manager")

tab1, tab2, tab3 = st.sidebar.tabs(["Add Node", "Edit Node", "Delete"])

# === TAB 1: ADD NODE ===
with tab1:
    st.subheader("Add New Event")

    # Filter out "Outcome" nodes (cannot attach children to endpoints)
    valid_parents = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'outcome'}

    if not valid_parents:
        st.error("No valid parents found. Please Reset.")
    else:
        parent_id = st.selectbox("Attach to Parent:", options=list(valid_parents.keys()),
                                 format_func=lambda x: valid_parents[x], key="add_parent")

        c1, c2 = st.columns(2)
        branch_type = c1.radio("Path?", ["Success (Yes)", "Failure (No)"], key="add_branch")
        node_type = c2.radio("Type?", ["Barrier", "Outcome"], key="add_type")

        new_name = st.text_input("Name", "New Barrier")

        if node_type == "Barrier":
            new_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01, key="add_prob")
        else:
            new_prob = 0.0  # Outcomes don't have success prob

        if st.button("Add Node"):
            new_id = str(uuid.uuid4())[:8]
            st.session_state.tree_nodes[new_id] = {
                "name": new_name,
                "type": "outcome" if node_type == "Outcome" else "event",
                "prob": new_prob,
                "path_prob": 0.0,  # Will be calculated immediately
                "parent_id": parent_id,
                "branch": branch_type
            }
            recalculate_tree()
            st.success("Added!")
            st.rerun()

# === TAB 2: EDIT NODE ===
with tab2:
    st.subheader("Edit Existing Node")

    # Can edit anything except Root (partially)
    edit_options = {k: v['name'] for k, v in st.session_state.tree_nodes.items()}
    edit_id = st.selectbox("Select Node:", options=list(edit_options.keys()), format_func=lambda x: edit_options[x],
                           key="edit_select")

    node_to_edit = st.session_state.tree_nodes[edit_id]

    # Edit Name
    edit_name = st.text_input("Edit Name", node_to_edit['name'], key="edit_name_input")

    # Edit Probability (Only for barriers, not outcomes or root)
    if node_to_edit['type'] == 'event':
        edit_prob = st.slider("Edit Success Prob", 0.0, 1.0, node_to_edit['prob'], 0.01, key="edit_prob_input")
    else:
        edit_prob = node_to_edit['prob']
        if node_to_edit['type'] == 'outcome':
            st.caption("Outcomes do not have internal success probabilities.")

    if st.button("Update Node"):
        st.session_state.tree_nodes[edit_id]['name'] = edit_name
        st.session_state.tree_nodes[edit_id]['prob'] = edit_prob
        recalculate_tree()  # This is crucial: updates all downstream math
        st.success("Updated!")
        st.rerun()

# === TAB 3: DELETE NODE ===
with tab3:
    st.subheader("Delete Branch")

    # Cannot delete Root
    del_options = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'root'}

    if not del_options:
        st.info("Nothing to delete (only Root exists).")
    else:
        del_id = st.selectbox("Select Node to Delete:", options=list(del_options.keys()),
                              format_func=lambda x: del_options[x], key="del_select")

        st.warning(f"⚠️ Warning: Deleting '{del_options[del_id]}' will also delete ALL nodes attached to it.")

        if st.button("Confirm Delete", type="primary"):
            delete_node(del_id)
            st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Reset Entire Tree"):
    st.session_state.tree_nodes = {}
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
    st.rerun()

# --- MAIN CANVAS ---
st.title("Event Tree Analysis")

# Build Graphviz dynamically from the clean state
dot = graphviz.Digraph()
dot.attr(rankdir='LR', splines='ortho')
dot.attr('node', fontname='Arial', fontsize='12')
dot.attr('edge', fontname='Arial', fontsize='10')

nodes = st.session_state.tree_nodes

# 1. Draw Nodes
for nid, node in nodes.items():
    if node['type'] == 'root':
        dot.node(nid, f"{node['name']}\n(Start)", shape='box', style='rounded,filled', fillcolor='#E3F2FD',
                 color='#1565C0')
    elif node['type'] == 'outcome':
        dot.node(nid, f"{node['name']}\nProb: {node['path_prob']:.4f}", shape='note', style='filled',
                 fillcolor='#F5F5F5', color='#424242')
    else:
        dot.node(nid, f"{node['name']}\n(Success: {node['prob']:.2f})", shape='box', style='filled',
                 fillcolor='#FFFFFF', color='#000000')

    # 2. Draw Edges (Connect to Parent)
    if node['parent_id']:
        parent = nodes[node['parent_id']]

        # Determine Label based on Branch + Parent Prob
        if parent['type'] == 'root':
            label = ""  # Root connection usually implies "It happened"
            color = "#555555"
        elif node['branch'] == "Success (Yes)":
            label = f"Yes\n({parent['prob']:.2f})"
            color = "#2E7D32"  # Green connection
        else:
            label = f"No\n({1.0 - parent['prob']:.2f})"
            color = "#C62828"  # Red connection

        dot.edge(node['parent_id'], nid, label=label, color=color, fontcolor=color)

st.graphviz_chart(dot)

# --- DEBUG / DATA VIEW ---
with st.expander("Engineering Data (Debug)"):
    st.write(st.session_state.tree_nodes)