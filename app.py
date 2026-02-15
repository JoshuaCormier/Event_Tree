import streamlit as st
import uuid
import json
import calculations as calc
import graph_renderer as rend

# --- CONFIG ---
st.set_page_config(page_title="Event Tree Manager", layout="wide")

# Hide the default Streamlit form instruction with CSS (just in case)
st.markdown("""
<style>
    [data-testid="stForm"] footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize State
calc.init_session_state()

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
            # border=False removes the box and the "Press Enter" text
            with st.form("add_node_form", border=False):
                c1, c2 = st.columns(2)
                branch = c1.radio("Path?", ["Success (Yes)", "Failure (No)"])
                n_type = c2.radio("Type?", ["Barrier", "Outcome"])
                n_name = st.text_input("Name", "New Event")

                n_prob = 0.0
                n_cost = 0.0

                if n_type == "Barrier":
                    n_prob = st.slider("Success Prob", 0.0, 1.0, 0.9, 0.01)
                elif n_type == "Outcome":
                    # Note: Do not use commas (e.g. 10000 not 10,000)
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

# TAB 2: EDIT
with tab2:
    st.subheader("Edit Node")
    nodes = st.session_state.tree_nodes
    if nodes:
        edit_opts = {}
        for nid, n in nodes.items():
            if n['type'] == 'root':
                label = f"ROOT: {n['name']}"
            else:
                p_name = nodes[n['parent_id']]['name'] if n['parent_id'] in nodes else "Unknown"
                branch = "Yes" if n['branch'] == "Success (Yes)" else "No"
                label = f"{n['name']} (from {p_name} via {branch})"
            edit_opts[nid] = label

        # Selector is OUTSIDE the form
        e_id = st.selectbox("Select Node to Edit:", list(edit_opts.keys()), format_func=lambda x: edit_opts[x])
        node = nodes[e_id]

        st.markdown(f"**Editing: {node['name']}**")

        # border=False removes the instruction text
        with st.form(key=f"edit_form_{e_id}", border=False):

            # Name Edit
            new_name = st.text_input("Node Name", value=node['name'])

            # Type Edit
            current_type = node['type']
            if current_type != 'root':
                type_idx = 0 if current_type == 'event' else 1
                new_type_display = st.selectbox("Node Type", ["Barrier", "Outcome"], index=type_idx)
                new_type = "event" if new_type_display == "Barrier" else "outcome"
            else:
                new_type = "root"

            st.divider()

            # Value Inputs
            new_prob = node.get('prob', 0.0)
            new_freq = node.get('freq', 1.0)
            new_cost = node.get('cost', 0.0)

            if new_type == 'root':
                st.markdown("### Frequency Input")
                new_freq = st.number_input("Events/Year", value=float(new_freq), step=0.01, format="%.5f")

            elif new_type == 'event':
                st.markdown("### Probability Input")
                new_prob = st.slider("Probability of Success", 0.0, 1.0, float(new_prob), 0.01)
                st.caption(f"Calculated Frequency: {node['path_freq']:.6f} /yr")

            elif new_type == 'outcome':
                st.markdown("### Cost Input")
                # Reminder: Type numbers only (no commas)
                new_cost = st.number_input("Financial Cost ($)", value=float(new_cost), step=1000.0)

                current_risk = node['path_freq'] * new_cost
                st.caption(f"Calculated Risk: ${current_risk:,.2f}")

            # SUBMIT BUTTON
            update_clicked = st.form_submit_button("Update Node")

            if update_clicked:
                nodes[e_id]['name'] = new_name
                nodes[e_id]['type'] = new_type
                nodes[e_id]['prob'] = new_prob
                nodes[e_id]['freq'] = new_freq
                nodes[e_id]['cost'] = new_cost

                calc.recalculate_tree()
                st.rerun()

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