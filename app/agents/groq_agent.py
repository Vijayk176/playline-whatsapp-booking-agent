import json
import logging
from groq import Groq
from app.config import settings
from app.agents.base import BaseAgent
from app.agents.tools import TOOL_DEFINITIONS

logger = logging.getLogger("groq_agent")

MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 5


class GroqAgent(BaseAgent):
    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not configured")
        self.client = Groq(api_key=settings.groq_api_key)

    async def respond(self, phone: str, history: list, tool_executor) -> str:
        messages = list(history)

        for _ in range(MAX_TOOL_ROUNDS):
            completion = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.4,
                max_tokens=500,
            )
            choice = completion.choices[0]
            msg = choice.message

            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = tool_executor.execute(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    })
                continue

            return msg.content or "Sorry, I didn't get that. Could you rephrase?"

        return "Sorry, I'm having trouble processing that. Let me connect you with our staff."
