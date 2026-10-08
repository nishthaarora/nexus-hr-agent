import os
from dotenv import load_dotenv
import json
from rag.bedrock_client import get_bedrock_client
from rag.exceptions import translate_client_error
from botocore.exceptions import ClientError

load_dotenv()

def summarize_if_needed(history):
    MAX_MESSAGES = 10
    RECENT_TO_KEEP = 4
    
    if (len(history) > MAX_MESSAGES):
        # send it to bedrock
        client = get_bedrock_client()
        messages_to_summarize = [
            m for m in history[:-RECENT_TO_KEEP]
            if all("text" in c for c in m["content"])
        ]
        
        if messages_to_summarize:
            try:
                response = client.converse(
                modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                messages=messages_to_summarize,
                system=[{"text": "summarize the conversation consisely in few sentences"}]
                )
                content = response["output"]["message"]["content"]
                text = next((c["text"] for c in content if "text" in c), None)
                if text is None:
                    # Model returned no usable text (e.g. empty content
                    # block) — skip summarizing this turn rather than crash.
                    return history
                return [{"role": "user", "content": [{"text": f"""here is the summary of earlier conversation: {text}"""}]}] + history[-RECENT_TO_KEEP:]
            except ClientError as exc:
                raise translate_client_error(exc) from exc
        else:
            return history
    else:
        return history
        