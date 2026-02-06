import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()

    # 1. VISUAL SETUP
    # splines='ortho': Strictly orthogonal (right-angled) lines.
    # nodesep='1.0': Increases vertical space between branches to prevent overlap.
    # ranksep='1.4': Increases horizontal space to give lines room to turn.
    dot.attr(rankdir='LR', splines='ortho', nodesep='1.0', ranksep='1.4')

    dot.attr('node', fontname='Arial', fontsize='12')

    nodes = st.session_state.tree_nodes

    for nid, n in nodes.items():
        # --- NODE DRAWING ---

        # 1. ROOT NODE (Fire Ignition)
        if n['type'] == 'root':
            lbl = f"{n['name']}"
            if is_risk_mode:
                freq_val = n.get('freq', 1.0)
                if freq_val < 0.001:
                    lbl += f"\nFreq: {freq_val:.2e}/yr"
                else:
                    lbl += f"\nFreq: {freq_val:.4f}/yr"

            dot.node(nid, lbl, shape='box', style='filled,rounded',
                     fillcolor='#EEEEEE', color='#222222', penwidth='2')

        # 2. OUTCOME NODE
        elif n['type'] == 'outcome':
            lbl = f"{n['name']}"
            if is_risk_mode:
                # Use scientific notation for very small numbers to keep box size manageable
                lbl += f"\nFreq: {n['path_freq']:.2e}/yr"
                lbl += f"\nCost: ${n.get('cost', 0):,.0f}"
                lbl += f"\nRisk: ${n.get('risk', 0):,.2f}/yr"
            else:
                lbl += f"\nProb: {n['path_prob']:.4f}"

            # Color logic
            color = '#F5F5F5'  # Default Gray
            if "Loss" in n['name'] or "Fatality" in n['name']: color = '#FFEBEE'  # Red tint
            if "Safe" in n['name'] or "Minor" in n['name']: color = '#E8F5E9'  # Green tint

            dot.node(nid, lbl, shape='note', style='filled', fillcolor=color)

        # 3. BARRIER NODE
        else:
            dot.node(nid, f"{n['name']}\n(P: {n['prob']:.2f})", shape='box', style='filled', fillcolor='white')

        # --- EDGE DRAWING ---
        if n['parent_id']:
            if n['parent_id'] in nodes:
                p = nodes[n['parent_id']]

                # Setup specific ports: Exit East (right), Enter West (left)
                # This prevents the "cutting through boxes" issue
                edge_attrs = {'tailport': 'e', 'headport': 'w'}

                # A. Connection from ROOT
                if p['type'] == 'root':
                    dot.edge(n['parent_id'], nid, color="#666666", penwidth='1.5', arrowsize='0.8', **edge_attrs)

                # B. Standard Connection
                else:
                    if n['branch'] == "Success (Yes)":
                        lbl = "Yes"
                        col = "#2E7D32"
                        prob_val = p['prob']
                    else:
                        lbl = "No"
                        col = "#C62828"
                        prob_val = 1.0 - p['prob']

                    lbl += f"\n({prob_val:.2f})"
                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col, fontsize='10', **edge_attrs)

    return dot