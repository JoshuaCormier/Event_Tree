import streamlit as st
import uuid
import json
import calculations as calc
import graph_renderer as rend

# --- CONFIG ---
st.set_page_config(page_title="Event Tree Manager", layout="wide")

# Initialize State
calc.init_session_state()

# --- SIDEBAR ---
st.sidebar.title("Risk Manager")
mode = st.sidebar.radio("Analysis Mode", ["Probability Only", "Risk (Frequency & Cost)"])
is_risk_mode = (mode == "Risk (Frequency & Cost)")
st.sidebar.markdown("---")

tab1, tab2, tab3, tab4 = st.sidebar.tabs(["Add", "Edit", "Delete", "File"])

# TAB 1: ADD
with tab1:
    st.subheader("Add Event")
    nodes = st.session_state.tree_nodes
    valid_parents = {k: v['name'] for k, v in nodes.items() if v['type'] != 'outcome'}

    if not valid_parents:
        st.error("No valid parents.")
    else:
        parent_id = st.selectbox("Parent:", list(valid_parents.keys()), format_func=lambda x: valid_parents[x])
        c1, c2 = st.columns(2)
        branch = c1.radio("Path?", ["Success (Yes)", "Failure (No)"])
        n_type = c2.radio("Type?", ["Barrier", "Outcome"])
        n_name = st.text_input("Name", "New Event")

        # Inputs depending on type
        n_prob = 0.0
        n_cost = 0.0
        if n_type == "Barrier":
            n_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01)
        elif n_type == "Outcome" and is_risk_mode:
            n_cost = st.number_input("Cost ($)", value=0.0, step=1000.0)

        if st.button("Add Node"):
            new_id = str(uuid.uuid4())[:8]
            st.session_state.tree_nodes[new_id] = {
                "name": n_name,
                "type": "outcome" if n_type == "Outcome" else "event",
                "prob": n_prob,
                "cost": n_cost,
                "parent_id": parent_id,
                "branch": branch,
                "freq": 0.0, "path_prob": 0.0, "path_freq": 0.0, "risk": 0.0  # Placeholders
            }
            calc.recalculate_tree()
            st.rerun()

# TAB 2: EDIT
with tab2:
    st.subheader("Edit Node")
    nodes = st.session_state.tree_nodes
    if nodes:
        opts = {k: v['name'] for k, v in nodes.items()}
        e_id = st.selectbox("Select:", list(opts.keys()), format_func=lambda x: opts[x])
        node = nodes[e_id]

        e_name = st.text_input("Name", node['name'], key="edt_name")

        # Variable inputs based on node type
        e_prob = node.get('prob', 0.0)
        e_freq = node.get('freq', 1.0)
        e_cost = node.get('cost', 0.0)

        if node['type'] == 'root' and is_risk_mode:
            e_freq = st.number_input("Events per Year", value=float(e_freq), step=0.1)
        elif node['type'] == 'event':
            e_prob = st.slider("Success Prob", 0.0, 1.0, float(e_prob), 0.01, key="edt_prob")
        elif node['type'] == 'outcome' and is_risk_mode:
            e_cost = st.number_input("Cost ($)", value=float(e_cost), step=1000.0, key="edt_cost")

        if st.button("Update"):
            nodes[e_id]['name'] = e_name
            nodes[e_id]['prob'] = e_prob
            nodes[e_id]['freq'] = e_freq
            nodes[e_id]['cost'] = e_cost
            calc.recalculate_tree()
            st.rerun()

# TAB 3: DELETE
with tab3:
    st.subheader("Delete")
    d_opts = {k: v['name'] for k, v in st.session_state.tree_nodes.items() if v['type'] != 'root'}
    if d_opts:
        d_id = st.selectbox("Delete:", list(d_opts.keys()), format_func=lambda x: d_opts[x])
        if st.button("Delete Branch", type="primary"):
            calc.delete_node(d_id)
            st.rerun()

# TAB 4: FILE
with tab4:
    st.subheader("File Ops")
    json_str = json.dumps(st.session_state.tree_nodes, indent=2)
    st.download_button("Download Tree (.json)", json_str, "tree.json", "application/json")
    st.markdown("---")
    u_file = st.file_uploader("Upload .json", type=["json"])
    if u_file and st.button("Load"):
        try:
            st.session_state.tree_nodes = json.load(u_file)
            calc.recalculate_tree()
            st.rerun()
        except:
            st.error("Error loading file.")

# --- MAIN CANVAS ---
title = "Quantitative Risk Analysis" if is_risk_mode else "Event Tree Analysis"
st.title(title)

# Generate and Display Graph
dot = rend.render_graph(is_risk_mode)
st.graphviz_chart(dot)

# Risk Summary
if is_risk_mode:
    total_risk = sum(n.get('risk', 0) for n in st.session_state.tree_nodes.values())
    st.markdown("### Risk Summary")
    st.metric("Total Annual Risk", f"${total_risk:,.2f}")