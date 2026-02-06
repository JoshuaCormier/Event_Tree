import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()

    # --- VISUAL SETUP ---
    # splines='ortho': Forces 90-degree lines.
    # nodesep='1.2': (Increased) Vertical space between branches to prevent "staircase" lines.
    # ranksep='2.5': (Increased) Horizontal space to prevent labels from breaking arrows.
    # ordering='out': Forces 'Yes' branch to stay above 'No' branch consistently.
    dot.attr(rankdir='LR', splines='ortho', nodesep='1.2', ranksep='2.5', ordering='out')

    # Global node settings
    # height='0.6': Fixed height ensures arrows always attach to the center.
    dot.attr('node', shape='rect', fontname='Arial', fontsize='12', margin='0.15', height='0.6', style='filled')

    # Global edge settings
    # penwidth='1.5': Thicker lines for a more professional schematic look.
    dot.attr('edge', fontname='Arial', fontsize='10', penwidth='1.5')

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
                lbl += f"\nFreq: {n['path_freq']:.2e}/yr"
                lbl += f"\nCost: ${n.get('cost', 0):,.0f}"
                lbl += f"\nRisk: ${n.get('risk', 0):,.2f}/yr"
            else:
                lbl += f"\nProb: {n['path_prob']:.4f}"

            color = '#F5F5F5'
            if "Loss" in n['name'] or "Fatality" in n['name']: color = '#FFEBEE'
            if "Safe" in n['name'] or "Minor" in n['name']: color = '#E8F5E9'

            dot.node(nid, lbl, shape='note', fillcolor=color)

        # 3. BARRIER NODE
        else:
            dot.node(nid, f"{n['name']}\n(P: {n['prob']:.2f})", shape='box', fillcolor='white')

        # --- EDGE DRAWING ---
        if n['parent_id']:
            if n['parent_id'] in nodes:
                p = nodes[n['parent_id']]

                # CRITICAL: Force strict East->West connections
                # This prevents the arrow from entering the top/bottom of a box.
                edge_attrs = {'tailport': 'e', 'headport': 'w'}

                # A. Connection from ROOT
                if p['type'] == 'root':
                    # Grey, thick neutral line
                    dot.edge(n['parent_id'], nid, color="#666666", arrowsize='0.8', **edge_attrs)

                # B. Standard Branches
                else:
                    if n['branch'] == "Success (Yes)":
                        lbl = "Yes"
                        col = "#2E7D32"  # Green
                        prob_val = p['prob']
                    else:
                        lbl = "No"
                        col = "#C62828"  # Red
                        prob_val = 1.0 - p['prob']

                    lbl += f"\n({prob_val:.2f})"

                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col, **edge_attrs)

    return dot