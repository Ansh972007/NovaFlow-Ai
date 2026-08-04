import time
import random

def run_sandbox_trial(graph_payload: dict, inject_error_node: str = "") -> dict:
    """Simulates execution of a Solution Graph, tracking latency and error triggers."""
    logs = []
    total_latency_ms = 0
    status = "success"
    
    nodes = graph_payload.get("nodes", {})
    for node_id, node_data in nodes.items():
        if inject_error_node == node_id:
            logs.append(f"Node [{node_id}]: Injected error triggered!")
            status = "failed"
            break
            
        # Simulate execution latency
        node_latency = random.randint(50, 150)
        total_latency_ms += node_latency
        logs.append(f"Node [{node_id}]: Executed successfully in {node_latency}ms")
        
    return {
        "status": status,
        "total_latency_ms": total_latency_ms,
        "logs": logs,
        "performance_profile": "optimal" if total_latency_ms < 1000 else "warning_latency"
    }
