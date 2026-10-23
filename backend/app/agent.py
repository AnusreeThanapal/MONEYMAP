"""
backend/app/agent.py
Advisor agent with Gemma 4 function calling.
System prompt enforces: always call a tool for numbers, never calculate yourself.
"""
import json
import os
from typing import Any

import ollama

from app.tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

MODEL      = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")
MAX_ITERS  = 4

SYSTEM_PROMPT = """You are MoneyMap, a careful personal finance assistant for Indian users.

STRICT RULES:
1. NEVER do arithmetic or calculate numbers yourself. 
2. ALWAYS call a tool for any number: spending amounts, net worth, savings, goals, anomalies.
3. After getting tool results, explain them in plain language using ₹ with Indian formatting (e.g. ₹2,45,000).
4. Be concise. Answer in 2-4 sentences maximum.
5. If asked about suspicious transactions, ALWAYS call detect_anomalies.
6. If asked about affording something, ALWAYS call project_goal with the exact rupee amount.

You serve Indian users. Use ₹ symbol always. Format large numbers Indian-style: ₹1,00,000 not ₹100,000."""


def run_agent(message: str, history: list[dict]) -> dict:
    """
    Run the advisor agent loop.
    Returns {answer, tool_calls} where tool_calls = [{name, arguments, result}].
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add (trimmed) history
    for h in history[-6:]:
        messages.append(h)

    messages.append({"role": "user", "content": message})

    tool_call_log = []
    answer        = ""
    retried       = False

    for iteration in range(MAX_ITERS):
        try:
            resp = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                options={"temperature": 0.1, "num_predict": 256},
            )
        except Exception as e:
            return {
                "answer":     f"Sorry, the AI model is unavailable: {str(e)[:100]}",
                "tool_calls": tool_call_log,
            }

        msg = resp["message"]

        # No tool calls → final answer
        if not msg.get("tool_calls"):
            answer = msg.get("content", "").strip()
            break

        # Execute each tool call
        messages.append({"role": "assistant", "content": None, "tool_calls": msg["tool_calls"]})

        for tc in msg["tool_calls"]:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"].get("arguments", {})

            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}

            fn = TOOL_FUNCTIONS.get(fn_name)
            if fn is None:
                result = {"error": f"Unknown tool: {fn_name}"}
            else:
                try:
                    result = fn(**fn_args)
                except Exception as e:
                    if not retried:
                        retried = True
                        result  = {"error": str(e), "note": "Tool failed, please try with corrected arguments"}
                    else:
                        result  = {"error": str(e)}

            result_str = json.dumps(result, default=str)
            tool_call_log.append({
                "name":      fn_name,
                "arguments": fn_args,
                "result":    result,
            })
            messages.append({
                "role":    "tool",
                "content": result_str,
            })
    else:
        # Hit max iterations
        answer = answer or "I reached my analysis limit. Please try a more specific question."

    if not answer:
        answer = "I was unable to produce a final answer. Please try again."

    return {"answer": answer, "tool_calls": tool_call_log}
