def optimize_route_latency(capability_id: str, available_providers: list[dict]) -> dict:
    """Dynamically identifies the lowest-latency available provider for a capability."""
    if not available_providers:
        raise ValueError("No providers available.")
        
    # Sort by mock latency budget in presets
    sorted_providers = sorted(available_providers, key=lambda p: p.get("latency", 500))
    return sorted_providers[0]
