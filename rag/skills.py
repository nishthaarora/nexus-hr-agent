from rag.tools import search_docs_tool_spec, create_ticket_tool_spec



DOCUMENTATION_SYSTEM_PROMPT = """
    You are an internal operation assistant that can find information in the company documentation.
    You have access to company documentation. You can search the documentation for the answer to the question.
    - If the user asks a question, answer it using your knowledge.
    - If the user asks a question that is not in the documentation, you can resond them to give more context about the question or tell them that you don't know the answer.
"""

SUPPORT_SYSTEM_PROMPT = """
    You are an internal operation assistant that can create tickets in the system.
    You have access to create support tickets.
    - If the user wants to create a ticket or report an issue, use the create_ticket tool.
    create_ticket tool.
"""

SKILLS = {
    "documentation": {
        "name": "documentation",
        "description": "search the documentation for the answer to the question",
        "tools": [search_docs_tool_spec()],
        "system_prompt": DOCUMENTATION_SYSTEM_PROMPT
    },
    "support": {
        "name": "support",
        "description": "create a support ticket for the question",
        "tools": [create_ticket_tool_spec()],
        "system_prompt": SUPPORT_SYSTEM_PROMPT
    }
}

