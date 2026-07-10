import boto3
from dotenv import load_dotenv
import json

load_dotenv()

def summarize_if_needed(history):
    MAX_MESSAGES = 10
    RECENT_TO_KEEP = 4
    
    if (len(history) > MAX_MESSAGES):
        # send it to bedrock
        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=history[:-RECENT_TO_KEEP],
            system=[{"text": "summarize the conversation consisely in few sentences"}]

        )
        print(response)
        text = response["output"]["message"]["content"][0]["text"]
        return [{"role": "user", "content": [{"text": f"""here is the summary of earlier conversation: {text}"""}]}] + history[-RECENT_TO_KEEP:]
    else: 
        return history
        
    
        