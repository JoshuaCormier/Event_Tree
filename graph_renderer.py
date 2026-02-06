import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()

    # --- VISUAL SETUP ---
    # splines='ortho': Forces 90-degree lines.
    # nodesep='1.0': Critical! Increases vertical space so lines have room to turn between boxes.
    # ranksep='2.0': Increases horizontal space for clear labels.
    # ordering='out': Keeps the 'Yes' branch physically above the 'No' branch (usually).
    dot.attr(rankdir='LR', splines='ortho', nodesep='1.0', ranksep='2.0', ordering='out')

    # Global node settings
    dot.attr('node', shape='rect', fontname='Arial', fontsize='12', margin='0.15', height='0.6')

    nodes = st.session_state.tree_nodes

    for nid, n in nodes.items():
        # --- NODE DRAWING ---

        # 1. ROOT NODE (Fire Ignition)
        if n['type'] == 'root':
            lbl = f"{n['name']}"
            if is_risk_mode:
                freq_val = n.get('freq', 1.0)
                # Clean formatting for scientific vs standard notation
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

                # CRITICAL FIX: Force arrows to exit East and enter West
                # This ensures they only point left-to-right
                edge_attrs = {'tailport': 'e', 'headport': 'w'}

                # A. Connection from ROOT
                if p['type'] == 'root':
                    dot.edge(n['parent_id'], nid, color="#666666", penwidth='1.5', arrowsize='0.8', **edge_attrs)

                # B. Standard Connection
                else:
                    if n['branch'] == "Success (Yes)":
                        lbl = "Yes"
                        col = "#2E7D32"  # Green
                        prob_val = p['prob']
                    else:
                        lbl = "No"
                        col = "#C62828"  # Red
                        prob_val = 1.0 - p['prob']

                    # Add Probability to Label
                    lbl += f"\n({prob_val:.2f})"

                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col, fontsize='10', **edge_attrs)

    return dot