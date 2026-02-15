import streamlit as st
import uuid
import json
import calculations as calc
import graph_renderer as rend

# --- CONFIG ---
st.set_page_config(page_title="Event Tree Manager", layout="wide")

# Initialize State
calc.init_session_state()


# --- CALLBACK FUNCTIONS (The Fix) ---
# These run immediately when you change a value, forcing a save BEFORE the page reloads.

def update_name(node_id):
    key = f"name_{node_id}"
    new_val = st.session_state[key]
    st.session_state.tree_nodes[node_id]['name'] = new_val


def update_cost(node_id):
    key = f"cost_{node_id}"
    new_val = st.session_state[key]
    st.session_state.tree_nodes[node_id]['cost'] = new_val
    calc.recalculate_tree()


def update_prob(node_id):
    key = f"prob_{node_id}"
    new_val = st.session_state[key]
    st.session_state.tree_nodes[node_id]['prob'] = new_val
    calc.recalculate_tree()


def update_freq(node_id):
    key = f"freq_{node_id}"
    new_val = st.session_state[key]
    st.session_state.tree_nodes[node_id]['freq'] = new_val
    calc.recalculate_tree()


def update_type(node_id):
    key = f"type_{node_id}"
    new_display_type = st.session_state[key]
    # Convert display name back to internal type
    internal_type = "event" if new_display_type == "Barrier" else "outcome"
    st.session_state.tree_nodes[node_id]['type'] = internal_type
    calc.recalculate_tree()


# --- SIDEBAR ---
st.sidebar.title("Risk Manager")

mode = st.sidebar.radio("View Mode", ["Probability Only", "Risk (Frequency & Cost)"])
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
        def get_unique_label(nid):
            n = nodes[nid]
            return f"{n['name']} ({nid[:4]})"


        parent_id = st.selectbox("Parent:", list(valid_parents.keys()), format_func=get_unique_label)

        parent_node = nodes[parent_id]
        has_child = any(n['parent_id'] == parent_id for n in nodes.values())

        if parent_node['type'] == 'root' and has_child:
            st.warning("⚠️ The Start Node can only connect to ONE first barrier.")
            st.button("Add Node", disabled=True)
        else:
            with st.form("add_node_form"):
                c1, c2 = st.columns(2)
                branch = c1.radio("Path?", ["Success (Yes)", "Failure (No)"])
                n_type = c2.radio("Type?", ["Barrier", "Outcome"])
                n_name = st.text_input("Name", "New Event")

                n_prob = 0.0
                n_cost = 0.0

                if n_type == "Barrier":
                    n_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01)
                elif n_type == "Outcome":
                    n_cost = st.number_input("Cost Consequence ($)", value=0.0, step=1000.0)

                submitted = st.form_submit_button("Add Node")

                if submitted:
                    new_id = str(uuid.uuid4())[:8]
                    st.session_state.tree_nodes[new_id] = {
                        "name": n_name,
                        "type": "outcome" if n_type == "Outcome" else "event",
                        "prob": n_prob,
                        "cost": n_cost,
                        "parent_id": parent_id,
                        "branch": branch,
                        "freq": 0.0, "path_prob": 0.0, "path_freq": 0.0, "risk": 0.0
                    }
                    calc.recalculate_tree()
                    st.rerun()

# TAB 2: EDIT (NOW USING LIVE CALLBACKS)
with tab2:
    st.subheader("Edit Node")
    nodes = st.session_state.tree_nodes
    if nodes:
        # Unique Selection Logic
        edit_opts = {}
        for nid, n in nodes.items():
            if n['type'] == 'root':
                label = f"ROOT: {n['name']}"
            else:
                p_name = nodes[n['parent_id']]['name'] if n['parent_id'] in nodes else "Unknown"
                branch = "Yes" if n['branch'] == "Success (Yes)" else "No"
                label = f"{n['name']} (from {p_name} via {branch})"
            edit_opts[nid] = label

        e_id = st.selectbox("Select Node to Edit:", list(edit_opts.keys()), format_func=lambda x: edit_opts[x])
        node = nodes[e_id]

        st.markdown(f"**Editing: {node['name']}**")
        st.caption("Changes save automatically when you press Enter or click away.")

        # 1. LIVE NAME EDIT
        st.text_input("Node Name", value=node['name'], key=f"name_{e_id}", on_change=update_name, args=(e_id,))

        # 2. LIVE TYPE EDIT
        current_type = node['type']
        if current_type != 'root':
            display_index = 0 if current_type == 'event' else 1
            st.selectbox("Node Type", ["Barrier", "Outcome"], index=display_index,
                         key=f"type_{e_id}", on_change=update_type, args=(e_id,))
            e_type = "event" if st.session_state[f"type_{e_id}"] == "Barrier" else "outcome"
        else:
            e_type = "root"
            st.info("Root node type cannot be changed.")

        st.divider()

        # 3. LIVE VALUE EDITING
        if e_type == 'root':
            st.markdown("### 1. Frequency Input")
            st.number_input("Events/Year", value=float(node.get('freq', 1.0)), step=0.01, format="%.5f",
                            key=f"freq_{e_id}", on_change=update_freq, args=(e_id,))

        elif e_type == 'event':
            st.markdown("### 1. Probability Input")
            st.slider("Probability of Success", 0.0, 1.0, float(node.get('prob', 0.9)), 0.01,
                      key=f"prob_{e_id}", on_change=update_prob, args=(e_id,))

            st.markdown("### 2. Frequency (Calculated)")
            st.caption(f"Rate: {node['path_freq']:.6f} /yr")

        elif e_type == 'outcome':
            st.markdown("### 1. Cost Input")
            # The 'on_change' here ensures the value is saved immediately when you hit Enter.
            st.number_input("Financial Cost ($)", value=float(node.get('cost', 0.0)), step=1000.0,
                            key=f"cost_{e_id}", on_change=update_cost, args=(e_id,))

            st.markdown("### 2. Risk Calculation")
            current_risk = node['path_freq'] * node.get('cost', 0.0)
            st.caption(f"Frequency: {node['path_freq']:.2e} /yr")
            st.metric("Annual Risk", f"${current_risk:,.2f}")

# TAB 3: DELETE
with tab3:
    st.subheader("Delete")
    d_opts = {}
    for nid, n in nodes.items():
        if n['type'] != 'root':
            p_name = nodes[n['parent_id']]['name'] if n['parent_id'] in nodes else "Unknown"
            d_opts[nid] = f"{n['name']} (Attached to: {p_name})"

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

dot = rend.render_graph(is_risk_mode)
st.graphviz_chart(dot)

if is_risk_mode:
    total_risk = sum(n.get('risk', 0) for n in st.session_state.tree_nodes.values())
    st.markdown("### Risk Summary")
    st.metric("Total Annual Risk", f"${total_risk:,.2f}")