import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', splines='ortho')
    dot.attr('node', fontname='Arial', fontsize='12')

    nodes = st.session_state.tree_nodes

    for nid, n in nodes.items():
        # --- NODE DRAWING ---

        # 1. ROOT NODE (Fire Ignition)
        if n['type'] == 'root':
            lbl = f"{n['name']}"
            if is_risk_mode:
                lbl += f"\nFreq: {n.get('freq', 1.0)}/yr"

            # Using 'box' instead of Mrecord to ensure compatibility and visibility
            dot.node(nid, lbl, shape='box', style='filled,rounded',
                     fillcolor='#EEEEEE', color='#222222', penwidth='2')

        # 2. OUTCOME NODE
        elif n['type'] == 'outcome':
            lbl = f"{n['name']}"
            if is_risk_mode:
                lbl += f"\nFreq: {n['path_freq']:.4f}/yr"
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
            # We look up the PARENT to check if it's the root
            if n['parent_id'] in nodes:
                p = nodes[n['parent_id']]

                # A. Connection from ROOT (No Yes/No text)
                if p['type'] == 'root':
                    dot.edge(n['parent_id'], nid, color="#666666", penwidth='1.5')

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
                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col)

    return dot