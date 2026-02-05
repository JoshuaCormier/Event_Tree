import streamlit as st
import graphviz
import uuid
import json
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
            "prob": 1.0,
            "path_prob": 1.0,
            "parent_id": None,
            "branch": None
        }
    }


# --- ENGINE: LOGIC & MATH ---
def recalculate_tree():
    """Re-runs the math for the entire tree."""
    nodes = st.session_state.tree_nodes
    # Find Root
    try:
        root_id = next(nid for nid, n in nodes.items() if n['type'] == 'root')
    except StopIteration:
        return  # Safety catch if tree is empty

    queue = deque([root_id])

    while queue:
        current_id = queue.popleft()
        current_node = nodes[current_id]

        children = [nid for nid, n in nodes.items() if n['parent_id'] == current_id]

        for child_id in children:
            child = nodes[child_id]
            if current_node['type'] == 'root':
                edge_prob = 1.0
            else:
                if child['branch'] == "Success (Yes)":
                    edge_prob = current_node['prob']
                else:
                    edge_prob = 1.0 - current_node['prob']

            child['path_prob'] = current_node['path_prob'] * edge_prob
            nodes[child_id] = child
            queue.append(child_id)


def delete_node(node_id):
    """Cascade delete."""

    def get_descendants(nid):
        descendants = []
        q = deque([nid])
        while q:
            curr = q.popleft()
            descendants.append(curr)
            children = [k for k, v in st.session_state.tree_nodes.items() if v['parent_id'] == curr]
            q.extend(children)
        return descendants

    targets = get_descendants(node_id)
    for t in targets:
        del st.session_state.tree_nodes[t]
    recalculate_tree()


# --- SIDEBAR ---
st.sidebar.title("🛠️ Tree Manager")
tab1, tab2, tab3, tab4 = st.sidebar.tabs(["Add", "Edit", "Delete", "File"])

# === TAB 1: ADD ===
with tab1:
    st.subheader("Add Event")
    valid_parents = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'outcome'}

    if not valid_parents:
        st.error("No valid parents.")
    else:
        parent_id = st.selectbox("Parent:", options=list(valid_parents.keys()), format_func=lambda x: valid_parents[x],
                                 key="add_p")
        c1, c2 = st.columns(2)
        branch = c1.radio("Path?", ["Success (Yes)", "Failure (No)"], key="add_b")
        n_type = c2.radio("Type?", ["Barrier", "Outcome"], key="add_t")
        n_name = st.text_input("Name", "New Event", key="add_n")

        n_prob = 0.0
        if n_type == "Barrier":
            n_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01, key="add_pr")

        if st.button("Add Node"):
            new_id = str(uuid.uuid4())[:8]
            st.session_state.tree_nodes[new_id] = {
                "name": n_name, "type": "outcome" if n_type == "Outcome" else "event",
                "prob": n_prob, "path_prob": 0.0, "parent_id": parent_id, "branch": branch
            }
            recalculate_tree()
            st.rerun()

# === TAB 2: EDIT ===
with tab2:
    st.subheader("Edit Node")
    opts = {k: v['name'] for k, v in st.session_state.tree_nodes.items()}
    e_id = st.selectbox("Select:", list(opts.keys()), format_func=lambda x: opts[x], key="edt_s")
    node = st.session_state.tree_nodes[e_id]

    e_name = st.text_input("Name", node['name'], key="edt_n")
    e_prob = node['prob']
    if node['type'] == 'event':
        e_prob = st.slider("Prob", 0.0, 1.0, node['prob'], 0.01, key="edt_p")

    if st.button("Update"):
        st.session_state.tree_nodes[e_id]['name'] = e_name
        st.session_state.tree_nodes[e_id]['prob'] = e_prob
        recalculate_tree()
        st.rerun()

# === TAB 3: DELETE ===
with tab3:
    st.subheader("Delete")
    d_opts = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'root'}
    if d_opts:
        d_id = st.selectbox("Select:", list(d_opts.keys()), format_func=lambda x: d_opts[x], key="del_s")
        if st.button("Delete Branch", type="primary"):
            delete_node(d_id)
            st.rerun()

# === TAB 4: FILE (SAVE/LOAD) ===
with tab4:
    st.subheader("💾 Save & Load")

    # DOWNLOAD
    st.markdown("### 1. Save Tree")
    # Convert dict to JSON string
    json_str = json.dumps(st.session_state.tree_nodes, indent=2)
    st.download_button(
        label="Download Tree (.json)",
        data=json_str,
        file_name="my_event_tree.json",
        mime="application/json"
    )

    st.markdown("---")

    # UPLOAD
    st.markdown("### 2. Load Tree")
    uploaded_file = st.file_uploader("Upload a .json file", type=["json"])

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            # Basic validation: Check if it looks like our tree
            if isinstance(data, dict) and any(n.get('type') == 'root' for n in data.values()):
                if st.button("Load from File"):
                    st.session_state.tree_nodes = data
                    recalculate_tree()  # Ensure math is fresh
                    st.success("Tree Loaded!")
                    st.rerun()
            else:
                st.error("Invalid file format.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# --- MAIN CANVAS ---
st.title("Event Tree Analysis")

dot = graphviz.Digraph()
dot.attr(rankdir='LR', splines='ortho')
dot.attr('node', fontname='Arial', fontsize='12')

for nid, n in st.session_state.tree_nodes.items():
    if n['type'] == 'root':
        dot.node(nid, f"{n['name']}\n(Start)", shape='box', style='rounded,filled', fillcolor='#E3F2FD',
                 color='#1565C0')
    elif n['type'] == 'outcome':
        # Color coding outcomes based on severity (simple logic)
        color = '#F5F5F5'
        if "Total Loss" in n['name'] or "Fatality" in n['name']: color = '#FFEBEE'  # Red tint
        if "Minor" in n['name']: color = '#E8F5E9'  # Green tint

        dot.node(nid, f"{n['name']}\nProb: {n['path_prob']:.4f}", shape='note', style='filled', fillcolor=color)
    else:
        dot.node(nid, f"{n['name']}\n(P: {n['prob']:.2f})", shape='box', style='filled', fillcolor='white')

    if n['parent_id']:
        p = st.session_state.tree_nodes[n['parent_id']]
        lbl = f"Yes\n({p['prob']:.2f})" if n['branch'] == "Success (Yes)" else f"No\n({1.0 - p['prob']:.2f})"
        col = "#2E7D32" if n['branch'] == "Success (Yes)" else "#C62828"
        dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col)

st.graphviz_chart(dot)