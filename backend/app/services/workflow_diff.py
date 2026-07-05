import json
from typing import Any


def _graph_maps(graph: dict) -> tuple[dict[str, dict], list[dict]]:
    nodes = {n["id"]: n for n in graph.get("nodes", []) if n.get("id")}
    edges = graph.get("edges") or []
    return nodes, edges


def _edge_key(edge: dict) -> str:
    return f"{edge.get('from')}->{edge.get('to')}"


def _node_summary(node: dict) -> dict:
    data = node.get("data") or {}
    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "label": data.get("label") or data.get("prompt", "")[:40] or node.get("type"),
    }


def diff_workflow_graphs(old_graph: dict, new_graph: dict) -> dict[str, Any]:
    old_nodes, old_edges = _graph_maps(old_graph)
    new_nodes, new_edges = _graph_maps(new_graph)

    old_edge_keys = {_edge_key(e) for e in old_edges}
    new_edge_keys = {_edge_key(e) for e in new_edges}

    nodes_added = [_node_summary(new_nodes[nid]) for nid in new_nodes if nid not in old_nodes]
    nodes_removed = [_node_summary(old_nodes[nid]) for nid in old_nodes if nid not in new_nodes]
    nodes_changed = []
    for nid in old_nodes:
        if nid in new_nodes and json.dumps(old_nodes[nid], sort_keys=True) != json.dumps(new_nodes[nid], sort_keys=True):
            nodes_changed.append(
                {
                    "id": nid,
                    "type": new_nodes[nid].get("type"),
                    "before": _node_summary(old_nodes[nid]),
                    "after": _node_summary(new_nodes[nid]),
                }
            )

    edges_added = [e for e in new_edges if _edge_key(e) not in old_edge_keys]
    edges_removed = [e for e in old_edges if _edge_key(e) not in new_edge_keys]

    return {
        "summary": {
            "nodes_added": len(nodes_added),
            "nodes_removed": len(nodes_removed),
            "nodes_changed": len(nodes_changed),
            "edges_added": len(edges_added),
            "edges_removed": len(edges_removed),
        },
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "nodes_changed": nodes_changed,
        "edges_added": edges_added,
        "edges_removed": edges_removed,
    }
