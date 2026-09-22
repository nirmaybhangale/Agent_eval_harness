# tests/test_agent.py
import pytest
import os
import json
from src.agent import run_support_agent
from tests.test_cases import test_cases
from tests.telemetry import test_results_log

# Mock prices for openai/gpt-oss-20b (as of mid-2026)
PRICE_PER_1M_INPUT = 0.075
PRICE_PER_1M_OUTPUT = 0.30

def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates the exact execution cost for a single run."""
    input_cost = (input_tokens / 1_000_000) * PRICE_PER_1M_INPUT
    output_cost = (output_tokens / 1_000_000) * PRICE_PER_1M_OUTPUT
    return input_cost + output_cost

@pytest.mark.asyncio
@pytest.mark.parametrize("case", test_cases, ids=lambda c: c["test_id"])
async def test_evaluate_agent_reliability(case):
    """
    The core reliability harness. Runs the agent, asserts on routing/parameters/outcomes, 
    and logs the cost and failure modes.
    """
    # 1. Execute the Agent
    result = await run_support_agent(case["user_input"])
    
    actual_tools = result["tool_calls"]
    final_response = result["final_response"].lower()
    
    # 2. Extract metrics
    cost = calculate_cost(result["total_prompt_tokens"], result["total_completion_tokens"])
    steps = len(actual_tools)
    
    passed = True
    failure_reasons = []

    # 3. Assert Routing & Extraction (The "What" and "How")
    # Did it call the exact expected tools with the exact arguments?
    for expected_tool in case["expected_tool_calls"]:
        match_found = False
        for actual_tool in actual_tools:
            if actual_tool["name"] == expected_tool["name"]:
                # Check args (simplified subset check for strings/floats)
                expected_args = expected_tool.get("args", {})
                actual_args = actual_tool.get("args", {})
                
                # If all expected key/values are present in the actual args, it's a match
                if all(actual_args.get(k) == v for k, v in expected_args.items()):
                    match_found = True
                    break
                else:
                    failure_reasons.append(f"Param extraction failed for {expected_tool['name']}. Expected: {expected_args}, Got: {actual_args}")
        
        if not match_found and not failure_reasons:
            failure_reasons.append(f"Expected tool '{expected_tool['name']}' was not called correctly.")
            passed = False

    # 4. Assert Safety Boundaries
    # Did it call a forbidden tool?
    for forbidden in case["forbidden_tools"]:
        if any(t["name"] == forbidden for t in actual_tools):
            failure_reasons.append(f"Agent violated boundaries: Called forbidden tool '{forbidden}'.")
            passed = False

    # 5. Assert Terminal State
    # Does the final response contain AT LEAST ONE of the expected substrings? (OR logic)
    if case["expected_substrings"]:
        found_any = any(req.lower() in final_response for req in case["expected_substrings"])
        if not found_any:
            failure_reasons.append(f"Final response missing expected keywords. Looked for any of: {case['expected_substrings']}")
            passed = False

    # 6. Log the results for Phase 3 reporting
    test_results_log.append({
        "test_id": case["test_id"],
        "category": case["category"],
        "passed": passed,
        "cost": cost,
        "steps": steps,
        "prompt_tokens": result["total_prompt_tokens"],
        "completion_tokens": result["total_completion_tokens"],
        "failure_reasons": " | ".join(failure_reasons) if failure_reasons else "None"
    })

    # 7. Final Pytest Assertion
    assert passed, f"Test Failed: {failure_reasons}\nAgent Response: {final_response}"