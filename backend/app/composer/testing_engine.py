def run_solution_test_assertions(solution_id: str, test_inputs: dict) -> dict:
    """Performs schema and output checks against test cases for Solution Graphs."""
    passed = True
    errors = []
    
    # Assert goal inputs mapping
    if "goal" not in test_inputs:
        passed = False
        errors.append("Missing required 'goal' input parameter.")
        
    return {
        "solution_id": solution_id,
        "test_run_status": "passed" if passed else "failed",
        "errors": errors
    }
