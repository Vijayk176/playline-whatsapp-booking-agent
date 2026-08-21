from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    async def respond(self, phone: str, history: list, tool_executor) -> str:
        """Given conversation history (list of {role, content}) and a tool executor,
        return the final natural-language reply to send to the customer."""
        raise NotImplementedError
