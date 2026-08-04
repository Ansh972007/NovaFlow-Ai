def migrate_legacy_workflow_to_solution(legacy_workflow: dict) -> dict:
    """Wraps and maps legacy workflow JSON schemas into new AIOS Solution Graph payloads."""
    legacy_nodes = legacy_workflow.get("nodes", [])
    legacy_edges = legacy_workflow.get("edges", [])
    
    nodes = {}
    edges = []
    
    for lnode in legacy_nodes:
        nid = lnode.get("id")
        nodes[nid] = {
            "type": lnode.get("type", "capability"),
            "status": "ready",
            "name": lnode.get("name", nid)
        }
        
    for ledge in legacy_edges:
        edges.append({
            "source": ledge.get("source"),
            "target": ledge.get("target")
        })
        
    return {
        "nodes": nodes,
        "edges": edges,
        "required_capabilities": list(nodes.keys())
    }
