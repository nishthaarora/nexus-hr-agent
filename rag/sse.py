import json
def sse_event(event: str, data: dict) -> str:
    """Format a single Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"