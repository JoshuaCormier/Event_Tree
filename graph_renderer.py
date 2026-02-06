import graphviz
import streamlit as st


def render_graph(is_risk_mode):
    dot = graphviz.Digraph()

    # VISUAL FIXES:
    # 1. splines='polyline': Uses angled straight lines that route AROUND boxes better than ortho.
    # 2. ranksep='1.2': Adds more horizontal space between steps.
    # 3. nodesep='0.8': Adds more vertical space between branches.
    dot.attr(rankdir='LR', splines='polyline', ranksep='1.2', nodesep='0.8')

    dot.attr('node', fontname='Arial', fontsize='12')

    nodes = st.session_state.tree_nodes

    for nid, n in nodes.items():
        # --- NODE DRAWING ---

        # 1. ROOT NODE (Fire Ignition)
        if n['type'] == 'root':
            lbl = f"{n['name']}"
            if is_risk_mode:
                # Show scientific notation if number is very small (e.g. 5e-06)
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
                lbl += f"\nFreq: {n['path_freq']:.2e}/yr"  # Scientific notation for space
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

                # A. Connection from ROOT
                if p['type'] == 'root':
                    dot.edge(n['parent_id'], nid, color="#666666", penwidth='1.5', arrowsize='0.8')

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
                    dot.edge(n['parent_id'], nid, label=lbl, color=col, fontcolor=col, fontsize='10')

    return dot