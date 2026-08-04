def mine_patterns(telemetry_logs: list[dict]) -> list[str]:
    """Scans telemetry log maps to extract repeating successful capability sequences."""
    sequences = []
    for log in telemetry_logs:
        path = log.get("execution_path", [])
        if len(path) >= 2 and log.get("success", False):
            sequences.append("->".join(path))
    return list(set(sequences))


def evolve_solution_graph(graph_payload: dict) -> dict:
    """Refactors solution graphs autonomously to prune redundant capability nodes."""
    nodes = graph_payload.get("nodes", {})
    edges = graph_payload.get("edges", [])
    
    # Prune isolated nodes (except standard db node)
    active_sources = {e["source"] for e in edges}
    active_targets = {e["target"] for e in edges}
    active_nodes = active_sources.union(active_targets)
    
    evolved_nodes = {}
    for nid, ndata in nodes.items():
        if nid in active_nodes or ndata.get("type") == "database" or nid == "cap_workflow":
            evolved_nodes[nid] = ndata
            
    return {
        "nodes": evolved_nodes,
        "edges": edges,
        "required_capabilities": graph_payload.get("required_capabilities", []),
        "evolved": len(evolved_nodes) < len(nodes)
    }
