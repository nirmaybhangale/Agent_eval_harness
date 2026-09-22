import json
import os
from dotenv import load_dotenv
from groq import AsyncGroq
from .tools import check_order_status, issue_refund, search_store_policies

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "openai/gpt-oss-20b"

# Define the JSON schemas for the tools so the LLM knows how to call them
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Check the shipping and delivery status of an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g., ORD-12345"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Issue a partial or full refund for a specific order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number", "description": "The exact refund amount as a float"}
                },
                "required": ["order_id", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_store_policies",
            "description": "Search the company knowledge base for return, refund, or shipping policies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The policy search query"}
                },
                "required": ["query"]
            }
        }
    }
]

# Map string names to actual mock functions
TOOL_REGISTRY = {
    "check_order_status": check_order_status,
    "issue_refund": issue_refund,
    "search_store_policies": search_store_policies
}

async def run_support_agent(user_input: str) -> dict:
    """
    Runs the agent loop for a single user query.
    Returns a dictionary containing the final response, tool trace, and aggregate token usage.
    """
    messages = [
        {
            "role": "system", 
            "content": "You are a strict, reliable E-Commerce Support Agent. Never guess parameters. Always use tools to look up information or perform actions."
        },
        {"role": "user", "content": user_input}
    ]

    execution_trace = {
        "tool_calls": [],
        "final_response": "",
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
    }

    # Maximum of 5 iterations to prevent infinite loops if the LLM gets confused
    for _ in range(5):
        # 1. Call the model with the current conversation history
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        
        # Accumulate usage metadata
        if response.usage:
            execution_trace["total_prompt_tokens"] += response.usage.prompt_tokens
            execution_trace["total_completion_tokens"] += response.usage.completion_tokens

        # 2. Check if the model wants to call any tools
        if message.tool_calls:
            #append the assistant's request to the messages array
            messages.append(message)
            
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                
                #wrap the JSON parsing in a try/except because the LLM might hallucinate malformed JSON
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Record what the LLM *attempted* to call so the harness can assert against it
                execution_trace["tool_calls"].append({
                    "name": func_name,
                    "args": args
                })

                # 3. Execute the tool if it exists in registry
                if func_name in TOOL_REGISTRY:
                    func = TOOL_REGISTRY[func_name]
                    # Our tools are async, so we await them
                    tool_result = await func(**args)
                else:
                    tool_result = f"Error: Tool '{func_name}' not found."

                # Append the tool's result to the history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(tool_result),
                })
        else:
            # If there are no tool calls, the model has reached its final terminal state
            execution_trace["final_response"] = message.content
            return execution_trace
            
    execution_trace["final_response"] = "Error: Maximum agent iterations reached."
    return execution_trace