import streamlit as st
import graphviz
import uuid
import json
from collections import deque

# --- PAGE CONFIG ---
st.set_page_config(page_title="Event Tree Risk Manager", layout="wide")

# --- SESSION STATE ---
if 'tree_nodes' not in st.session_state:
    root_id = str(uuid.uuid4())[:8]
    st.session_state.tree_nodes = {
        root_id: {
            "name": "Fire Ignition",
            "type": "root",
            "prob": 1.0,  # In Risk Mode, this is ignored in favor of 'freq'
            "freq": 1.0,  # Events per year
            "path_prob": 1.0,
            "path_freq": 1.0,  # Cumulative frequency
            "cost": 0.0,  # Cost (only for outcomes)
            "risk": 0.0,  # Risk = Freq * Cost
            "parent_id": None,
            "branch": None
        }
    }


# --- ENGINE: LOGIC & MATH ---
def recalculate_tree():
    """Recalculates Probabilities AND Frequencies/Risks."""
    nodes = st.session_state.tree_nodes
    try:
        root_id = next(nid for nid, n in nodes.items() if n['type'] == 'root')
    except StopIteration:
        return

        # Update Root Logic
    root = nodes[root_id]
    root['path_prob'] = 1.0
    # In Risk Mode, the path frequency starts with the Root Frequency
    root['path_freq'] = root.get('freq', 1.0)
    nodes[root_id] = root

    queue = deque([root_id])

    while queue:
        current_id = queue.popleft()
        current_node = nodes[current_id]

        children = [nid for nid, n in nodes.items() if n['parent_id'] == current_id]

        for child_id in children:
            child = nodes[child_id]

            # 1. Determine Edge Probability
            if current_node['type'] == 'root':
                edge_prob = 1.0  # Root always happens if defined
            else:
                if child['branch'] == "Success (Yes)":
                    edge_prob = current_node['prob']
                else:
                    edge_prob = 1.0 - current_node['prob']

            # 2. Calculate Math
            child['path_prob'] = current_node['path_prob'] * edge_prob
            child['path_freq'] = current_node['path_freq'] * edge_prob

            # 3. Calculate Risk (Only meaningful for Outcomes, but calculated for all)
            child_cost = child.get('cost', 0.0)
            child['risk'] = child['path_freq'] * child_cost

            nodes[child_id] = child
            queue.append(child_id)


def delete_node(node_id):
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
st.sidebar.title("Risk Manager")

# 1. MODE SELECTION
mode = st.sidebar.radio("Analysis Mode", ["Probability Only", "Risk (Frequency & Cost)"])
is_risk_mode = (mode == "Risk (Frequency & Cost)")

st.sidebar.markdown("---")

tab1, tab2, tab3, tab4 = st.sidebar.tabs(["Add", "Edit", "Delete", "File"])

# === TAB 1: ADD ===
with tab1:
    st.subheader("Add Event")
    valid_parents = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'outcome'}

    if not valid_parents:
        st.error("No valid parents.")
    else:
        parent_id = st.selectbox("Parent:", list(valid_parents.keys()), format_func=lambda x: valid_parents[x],
                                 key="a_p")
        c1, c2 = st.columns(2)
        branch = c1.radio("Path?", ["Success (Yes)", "Failure (No)"], key="a_b")
        n_type = c2.radio("Type?", ["Barrier", "Outcome"], key="a_t")
        n_name = st.text_input("Name", "New Event", key="a_n")

        n_prob = 0.0
        n_cost = 0.0

        if n_type == "Barrier":
            n_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01, key="a_pr")
        elif n_type == "Outcome" and is_risk_mode:
            n_cost = st.number_input("Cost Consequence ($)", min_value=0.0, value=10000.0, step=1000.0, key="a_c")

        if st.button("Add Node"):
            new_id = str(uuid.uuid4())[:8]
            st.session_state.tree_nodes[new_id] = {
                "name": n_name,
                "type": "outcome" if n_type == "Outcome" else "event",
                "prob": n_prob,
                "cost": n_cost,
                "freq": 0.0,  # Placeholder
                "path_prob": 0.0,
                "path_freq": 0.0,
                "risk": 0.0,
                "parent_id": parent_id,
                "branch": branch
            }
            recalculate_tree()
            st.rerun()

# === TAB 2: EDIT ===
with tab2:
    st.subheader("Edit Node")
    opts = {k: v['name'] for k, v in st.session_state.tree_nodes.items()}
    e_id = st.selectbox("Select:", list(opts.keys()), format_func=lambda x: opts[x], key="e_s")
    node = st.session_state.tree_nodes[e_id]

    # Common Edits
    e_name = st.text_input("Name", node['name'], key="e_n")

    # Specific Edits
    e_prob = node.get('prob', 0.0)
    e_freq = node.get('freq', 1.0)
    e_cost = node.get('cost', 0.0)

    if node['type'] == 'root':
        if is_risk_mode:
            e_freq = st.number_input("Initiating Frequency (Events/Year)", value=float(e_freq), step=0.1, key="e_f")

    elif node['type'] == 'event':
        e_prob = st.slider("Success Prob", 0.0, 1.0, float(e_prob), 0.01, key="e_p")

    elif node['type'] == 'outcome':
        if is_risk_mode:
            e_cost = st.number_input("Cost Consequence ($)", value=float(e_cost), step=1000.0, key="e_c")

    if st.button("Update"):
        st.session_state.tree_nodes[e_id]['name'] = e_name
        st.session_state.tree_nodes[e_id]['prob'] = e_prob
        st.session_state.tree_nodes[e_id]['freq'] = e_freq
        st.session_state.tree_nodes[e_id]['cost'] = e_cost
        recalculate_tree()
        st.rerun()

# === TAB 3: DELETE ===
with tab3:
    st.subheader("Delete")
    d_opts = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'root'}
    if d_opts:
        d_id = st.selectbox("Select:", list(d_opts.keys()), format_func=lambda x: d_opts[x], key="d_s")
        if st.button("Delete Branch", type="primary"):
            delete_node(d_id)
            st.rerun()

# === TAB 4: FILE ===
with tab4:
    st.subheader("File Ops")
    json_str = json.dumps(st.session_state.tree_nodes, indent=2)
    st.download_button("Download Tree (.json)", json_str, "risk_tree.json", "application/json")

    st.markdown("---")
    u_file = st.file_uploader("Upload .json", type=["json"])
    if u_file and st.button("Load"):
        try:
            data = json.load(u_file)
            st.session_state.tree_nodes = data
            recalculate_tree()
            st.rerun()
        except:
            st.error("Error loading file.")

# --- MAIN CANVAS ---
title_prefix = "Quantitative Risk" if is_risk_mode else "Event Tree"
st.title(f"{title_prefix} Analysis")

dot = graphviz.Digraph()
dot.attr(rankdir='LR', splines='ortho')
dot.attr('node', fontname='Arial', fontsize='12')

total_risk = 0.0

for nid, n in st.session_state.tree_nodes.items():
    # 1. ROOT NODE (Professional Engineering Style)
    if n['type'] == 'root':
        lbl = f"{n['name']}"
        if is_risk_mode:
            lbl += f"\nFreq: {n.get('freq', 1.0)}/yr"

        # Mrecord gives slightly rounded corners, distinct from standard boxes
        # penwidth=2 makes the border thicker/bolder
        # fillcolor is a neutral, professional grey
        dot.node(nid, lbl, shape='Mrecord', style='filled,rounded', fillcolor='#EEEEEE', color='#222222',
                 penwidth='2.0')

    # 2. OUTCOME NODE
    elif n['type'] == 'outcome':
        # Probability Mode Label
        lbl = f"{n['name']}\nProb: {n['path_prob']:.4f}"

        # Risk Mode Label additions
        if is_risk_mode:
            lbl = f"{n['name']}\nFreq: {n['path_freq']:.4f}/yr"
            lbl += f"\nCost: ${n.get('cost', 0):,.0f}"
            lbl += f"\nRisk: ${n.get('risk', 0):,.2f}/yr"
            total_risk += n.get('risk', 0)

        color = '#F5F5F5'
        if "Loss" in n['name']: color = '#FFEBEE'
        dot.node(nid, lbl, shape='note', style='filled', fillcolor=color)

    # 3. BARRIER NODE
    else:
        dot.node(nid, f"{n['name']}\n(P: {n['prob']:.2f})", shape='box', style='filled', fillcolor='white')

    # EDGE DRAWING
    if n['parent_id']:
        p = st.session_state.tree_nodes[n['parent_id']]
        if n['branch'] == "Success (Yes)":
            lbl = f"Yes"
            col = "#2E7D32"
        else:
            lbl = f"No"
            col = "#C62828"

        # Add probability to edge label
        lbl += f"\n({p.get('prob', 0) if n['branch'] == 'Success (Yes)' else 1.0 - p.get('prob', 0):.2f})"

        dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col)

st.graphviz_chart(dot)

# --- SUMMARY METRICS ---
if is_risk_mode:
    st.markdown("### Annual Risk Summary")
    c1, c2 = st.columns(2)
    c1.metric("Total Annual Risk (Expected Loss)", f"${total_risk:,.2f}")

    # Find highest risk path
    outcomes = [n for n in st.session_state.tree_nodes.values() if n['type'] == 'outcome']
    if outcomes:
        worst = max(outcomes, key=lambda x: x['risk'])
        c2.metric("Highest Risk Scenario", worst['name'], f"${worst['risk']:,.2f}/yr")