from botocore.exceptions import ClientError

class AgentError(Exception):
    """Base class for agent-level errors that map to a specific API response."""
    
class MaxTokensReachedError(AgentError):
     """The model's response was truncated by the max token limit."""

class TooManyToolCallsError(AgentError):
     """The agent exceeded its tool-call recursion budget without a final answer."""

class RateLimitedError(AgentError):
     """Bedrock is throttling requests."""
     
class ContextTooLargeError(AgentError):
    """The conversation exceeds the model's context window."""
    

def translate_client_error(exc: ClientError) -> AgentError:
     """Map a raw Bedrock ClientError to one of our typed exceptions."""
     error_code = exc.response["Error"]["Code"]
     if error_code == "ThrottlingException":
        return RateLimitedError("Bedrock is throttling requests — please try again shortly.")
     if error_code == "ValidationException" and "too long" in str(exc).lower():
        return ContextTooLargeError("Conversation is too long for the model's context window.")
     return AgentError(f"Bedrock request failed: {exc}")