from rag.query import ask

def create_ticket_tool_spec():
    """
    Returns the JSON Schema specification for the Weather tool. The tool specification
    defines the input schema and describes the tool's functionality.
    For more information, see https://json-schema.org/understanding-json-schema/reference.

    :return: The tool specification for the Weather tool.
    """
    return {
        "toolSpec": {
            "name": "create_ticket",
            "description": "given the title and description of the ticket create a ticket in the system.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "this is the title of the ticket",
                        },
                        "description": {
                            "type": "string",
                            "description": "This is the description of the ticket",
                        },
                    },
                    "required": ["title", "description"],
                }
            },
        }
    }

def search_docs_tool_spec():
    """
    Returns the JSON Schema specification for the Weather tool. The tool specification
    defines the input schema and describes the tool's functionality.
    For more information, see https://json-schema.org/understanding-json-schema/reference.

    :return: The tool specification for the Weather tool.
    """
    return {
        "toolSpec": {
            "name": "search_docs",
            "description": "given the query, search the company documentation and return the relevant documents.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "the question to search documentation for",
                        },
                    },
                    "required": ["query"],
                }
            },
        }
    }
    


def create_ticket(title: str, description: str):
    ticket_id = "TICKET-123456"
    return {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "status": "created",
    }
    
def search_docs(query: str):
    answer = ask(query)
    return {"result": answer}