def estimate_solution_resources(required_capabilities: list[str]) -> dict:
    """Estimates the required hardware resources (threads, RAM, VRAM) for a set of capabilities."""
    vram_gb = 0.0
    ram_mb = 128
    threads = 1
    
    for cap in required_capabilities:
        if cap == "cap_voice":
            vram_gb += 4.0
            ram_mb += 1024
            threads += 2
        elif cap == "cap_ocr":
            vram_gb += 2.0
            ram_mb += 512
            threads += 1
        elif cap == "cap_knowledge":
            ram_mb += 256
            threads += 1
            
    return {
        "vram_allocation_gb": vram_gb,
        "ram_allocation_mb": ram_mb,
        "worker_threads": threads,
        "priority_class": "high" if vram_gb > 0 else "standard"
    }


def schedule_solution_task(task_type: str, payload: dict) -> str:
    """Schedules tasks to execute in one of three running modes: cron, batch, or realtime."""
    if task_type in ("voice_stream", "ocr_instant"):
        return "realtime_worker_queue"
    elif task_type in ("knowledge_index_sync", "batch_ocr"):
        return "batch_worker_queue"
    return "standard_cron_schedule"
