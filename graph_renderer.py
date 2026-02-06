import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()

    # --- VISUAL SETUP ---
    # splines='ortho': Forces 90-degree lines.
    # nodesep='0.8': Vertical space between branches.
    # ranksep='1.5': Horizontal space (Critical for preventing 'floating' arrows).
    dot.attr(rankdir='LR', splines='ortho', nodesep='0.8', ranksep='1.5')

    # Global node settings
    dot.attr('node', shape='rect', fontname='Arial', fontsize='12', margin='0.15', height='0.5')

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

            dot.node(nid, lbl, shape='note', style='filled', fillcolor=color)

        # 3. BARRIER NODE
        else:
            dot.node(nid, f"{n['name']}\n(P: {n['prob']:.2f})", shape='box', style='filled', fillcolor='white')

        # --- EDGE DRAWING ---
        if n['parent_id']:
            if n['parent_id'] in nodes:
                p = nodes[n['parent_id']]

                # CRITICAL VISUAL FIXES
                # 1. tailport='e', headport='w': Forces lines to stick to the sides (Left-to-Right only).
                # 2. constraint='true': Forces the tree hierarchy to remain rigid.
                edge_attrs = {'tailport': 'e', 'headport': 'w'}

                # A. Connection from ROOT (The "Stem")
                # We draw this as a neutral grey line, ignoring Yes/No logic.
                if p['type'] == 'root':
                    dot.edge(n['parent_id'], nid, color="#666666", penwidth='2.0', arrowsize='0.8', **edge_attrs)

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

                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col, fontsize='10', **edge_attrs)

    return dot