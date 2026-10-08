import logging
from botocore.exceptions import ClientError
from rag.tools import TOOL_REGISTRY
from dotenv import load_dotenv
from rag.exceptions import (
    MaxTokensReachedError,
    TooManyToolCallsError,
    RateLimitedError,
    ContextTooLargeError,
    AgentError,
)
import json
from rag.bedrock_client import get_bedrock_client

from rag.sse import sse_event
from rag.exceptions import translate_client_error
import os


load_dotenv()
logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION")
MODEL_ID = os.getenv("MODEL_ID")


MAX_RECURSIONS = 5
class UserAgentTool:
    def __init__(self):
         # Create a Bedrock Runtime client in the specified AWS Region.
        self.bedrockRuntimeClient = get_bedrock_client()
        self.tools_used = []

    def run(self, session: dict):
        conversation = session["history"]
        tools = session["tools"]
        system_prompt = session["system_prompt"]

        self.tools_used = []

        # Send the conversation to Amazon Bedrock
        bedrock_response = self._send_conversation_to_bedrock(conversation, tools, system_prompt)
        print('bedrock_response',bedrock_response)
        # Recursively handle the model's response until the model has returned
        # its final response or the recursion counter has reached 0
        message = self._process_model_response(
            bedrock_response, conversation, tools, system_prompt, max_recursion=MAX_RECURSIONS
        )
        return message, self.tools_used

    def _send_conversation_to_bedrock(self, conversation, tools, system_prompt):
        try:
            return self.bedrockRuntimeClient.converse(
                modelId=MODEL_ID,
                # inferenceConfig={"maxTokens": 400},
                messages=conversation,
                system=[{"text": system_prompt}],
                toolConfig={"tools": tools},
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ThrottlingException":
                raise RateLimitedError("Bedrock is throttling requests — please try again shortly.") from exc
            if error_code == "ValidationException" and "too long" in str(exc).lower():
                raise ContextTooLargeError("Conversation is too long for the model's context window.") from exc
            raise

    def _send_conversation_to_bedrock_stream(self, conversation, tools, system_prompt):
        try:
            return self.bedrockRuntimeClient.converse_stream(
                modelId=MODEL_ID,
                # inferenceConfig={"maxTokens": 400},
                messages=conversation,
                system=[{"text": system_prompt}],
                toolConfig={"tools": tools},
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ThrottlingException":
                raise RateLimitedError("Bedrock is throttling requests — please try again shortly.") from exc
            if error_code == "ValidationException" and "too long" in str(exc).lower():
                raise ContextTooLargeError("Conversation is too long for the model's context window.") from exc
            raise
            
    def stream(self, session: dict) :
        """Yield SSE-formatted strings for this turn, handling the full tool-call loop."""
        conversation = session["history"]
        tools = session["tools"]
        system_prompt = session["system_prompt"]
        self.tools_used = []
        yield sse_event("message_start", {})
        
        max_recursion = MAX_RECURSIONS
        try:
            while True:
                stream_response = self._send_conversation_to_bedrock_stream(conversation, tools, system_prompt)
                
                stop_reason = None
                content_blocks: list[dict] = []
                current_block: dict | None = None
                tool_input_json = ""
                
                for event in stream_response["stream"]:
                    # print('event**************', event)
                    if "contentBlockStart" in event:
                        start = event["contentBlockStart"]["start"]
                        if "toolUse" in start:
                            current_block = {"toolUse": {
                                "toolUseId": start["toolUse"]["toolUseId"],
                                "name": start["toolUse"]["name"],
                                "input": {},
                            }}
                            tool_input_json = ""
                            yield sse_event("tool_use", {"tool_name": start["toolUse"]["name"]})
                        else:
                            current_block = {"text": ""}
                    elif "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"]["delta"]
                        if "text" in delta:
                            if current_block is None:
                                current_block = {"text": ""}
                            current_block["text"] += delta["text"]
                            yield sse_event("text_chunk", {"text": delta["text"]})
                        elif "toolUse" in delta:
                            tool_input_json += delta["toolUse"].get("input", "")
                            
                    elif "contentBlockStop" in event:
                        if current_block and "toolUse" in current_block:
                            try: 
                                current_block["toolUse"]["input"] = json.loads(tool_input_json) if tool_input_json else {}
                            except json.JSONDecodeError:
                                current_block["toolUse"]["input"] = {}
                        if current_block:
                            content_blocks.append(current_block)
                        current_block = None
                    elif "messageStop" in event:
                        stop_reason = event["messageStop"]["stopReason"]
                        
                if stop_reason == "max_tokens":
                    raise MaxTokensReachedError("Response was cut off — it exceeded the model's max token limit.")
                
                assistant_message = {"role": "assistant", "content": content_blocks}
                
                if stop_reason != "tool_use":
                    conversation.append(assistant_message)
                    yield sse_event("message_end", {}) 
                    return
            
                if max_recursion <= 0:
                    raise TooManyToolCallsError("Agent made too many tool calls without reaching a final answer.")
                
                tool_use_block = next((b["toolUse"] for b in content_blocks if "toolUse" in b), None)
                if tool_use_block is None:
                    conversation.append(assistant_message)
                    yield sse_event("message_end", {}) 
                    return
                
                tool_name = tool_use_block["name"]
                tool_input = tool_use_block["input"]
                self.tools_used.append(tool_name)
                tool_fn = TOOL_REGISTRY.get(tool_name)
                if tool_fn is None:
                    tool_response = {"error": f"Unknown tool {tool_name}"}
                else:
                    try:
                        tool_response = tool_fn(**tool_input)
                    except Exception as exc:
                        tool_response = {"error": f"Tool {tool_name} failed: {exc}"}
                
                conversation.append(assistant_message)
                conversation.append({
                    "role": "user",
                    "content": [{"toolResult": {
                        "toolUseId": tool_use_block["toolUseId"],
                        "content": [{"text": str(tool_response)}],
                    }}]
                })
                max_recursion -= 1
        except MaxTokensReachedError as exc:                            
            yield sse_event("max_tokens_reached", {"detail": str(exc)})
        except RateLimitedError as exc:
            yield sse_event("rate_limited", {"detail": str(exc)})
        except ContextTooLargeError as exc:
            yield sse_event("context_too_large", {"detail": str(exc)})
        except AgentError as exc:
            yield sse_event("error", {"detail": str(exc)})

        
             
    def _process_model_response(self, bedrock_response, conversation, tools, system_prompt, max_recursion):
        while True: 
            stop_reason = bedrock_response["stopReason"]
            
            if stop_reason == "max_tokens":
                raise MaxTokensReachedError("Response was cut off — it exceeded the model's max token limit.")
            if stop_reason != "tool_use":
                return bedrock_response["output"]["message"]
            
            if max_recursion <= 0:
                raise TooManyToolCallsError("Agent made too many tool calls without reaching a final answer.")
            

            content = bedrock_response["output"]["message"]["content"]
            tool_use = next((item["toolUse"] for item in content if "toolUse" in item), None)
            
            if not tool_use:
                return bedrock_response["output"]["message"]
            
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            self.tools_used.append(tool_name)
            
            tool_fn = TOOL_REGISTRY.get(tool_name)
            if tool_fn is None:
                tool_response = {"error": f"Unknown tool {tool_name}"}
            else:
                try:
                    tool_response = tool_fn(**tool_input)
                except Exception as exc:
                    tool_response = {"error": f"Tool {tool_name} failed: {exc}"}

            conversation.append(bedrock_response["output"]["message"])
            conversation.append({
                "role": "user",
                "content": [{"toolResult": {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [{"text": str(tool_response)}],
                }}]
            })
    
    
            
            bedrock_response = self._send_conversation_to_bedrock(conversation, tools, system_prompt)
            max_recursion -= 1
        


def run_agent(session: dict):
    agent = UserAgentTool()
    return agent.run(session)


if __name__ == "__main__":
    tool_use_demo = UserAgentTool()
    tool_use_demo.run()
