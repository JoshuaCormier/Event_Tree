import uuid
from collections import deque
import streamlit as st


def init_session_state():
    if 'tree_nodes' not in st.session_state:
        root_id = str(uuid.uuid4())[:8]
        st.session_state.tree_nodes = {
            root_id: {
                "name": "Fire Ignition",
                "type": "root",
                "prob": 1.0,
                "freq": 1.0,  # Default: 1 event per year
                "path_prob": 1.0,
                "path_freq": 1.0,
                "cost": 0.0,
                "risk": 0.0,
                "parent_id": None,
                "branch": None
            }
        }


def recalculate_tree():
    """Traverses tree to update Probability, Frequency, and Risk."""
    nodes = st.session_state.tree_nodes

    # 1. Find Root
    try:
        root_id = next(nid for nid, n in nodes.items() if n['type'] == 'root')
    except StopIteration:
        return  # Empty tree safety

    # 2. Reset Root Values
    root = nodes[root_id]
    root['path_prob'] = 1.0
    root['path_freq'] = root.get('freq', 1.0)  # Use user-defined frequency
    nodes[root_id] = root

    # 3. BFS Traversal
    queue = deque([root_id])

    while queue:
        current_id = queue.popleft()
        current_node = nodes[current_id]

        children = [nid for nid, n in nodes.items() if n['parent_id'] == current_id]

        for child_id in children:
            child = nodes[child_id]

            # Connection Logic
            if current_node['type'] == 'root':
                edge_prob = 1.0
            else:
                if child['branch'] == "Success (Yes)":
                    edge_prob = current_node['prob']
                else:
                    edge_prob = 1.0 - current_node['prob']

            # Math Updates
            child['path_prob'] = current_node['path_prob'] * edge_prob
            child['path_freq'] = current_node['path_freq'] * edge_prob

            # Risk Calculation (Risk = Freq * Cost)
            child_cost = child.get('cost', 0.0)
            child['risk'] = child['path_freq'] * child_cost

            nodes[child_id] = child
            queue.append(child_id)


def delete_node(node_id):
    """Deletes a node and all its descendants."""

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