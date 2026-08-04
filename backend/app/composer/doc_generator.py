def generate_solution_documentation(solution_id: str, graph_payload: dict) -> str:
    """Autonomously compiles markdown documentation summary files for deployed graphs."""
    nodes = graph_payload.get("nodes", {})
    edges = graph_payload.get("edges", [])
    
    doc = []
    doc.append(f"# Deployed Solution Guide: {solution_id}")
    doc.append("\nThis document lists the operational capabilities and connections deployed by NovaFlow AIOS.\n")
    
    doc.append("## Deployed Capabilities")
    for nid, ndata in nodes.items():
        doc.append(f"- **{nid}**: type=`{ndata.get('type')}`")
        
    doc.append("\n## Inter-node Connections")
    for edge in edges:
        doc.append(f"- {edge['source']} ---> {edge['target']}")
        
    return "\n".join(doc)
