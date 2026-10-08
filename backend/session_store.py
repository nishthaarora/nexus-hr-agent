
import os
import json
from dotenv import load_dotenv
from rag.skills import SKILLS
from rag.bedrock_client import get_bedrock_client
from rag.exceptions import translate_client_error
from botocore.exceptions import ClientError
load_dotenv()

client = get_bedrock_client()

SESSIONS_DIR = 'sessions'

def add_history(history, message):
    history.append(message)
    return history

def save_history(session_id, content):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f'{session_id}.json')
    with open(path, 'w') as file:
        json.dump(content, file)
        
        
def load_or_create_session(session_id, content_message=None):
    file_path = os.path.join(SESSIONS_DIR, f'{session_id}.json')
    if not os.path.exists(file_path) and content_message:
        intent = get_intent(content_message)
        skill = SKILLS[intent]
        data = {
            "session_id": session_id,
            "intent": intent,
            "tools": skill["tools"],
            "system_prompt": skill["system_prompt"],
            "history": add_history([], {"role": "user", "content": [{"text": content_message}]})
        }
        save_history(session_id, data)
        return data
    elif content_message:
        with open(file_path, 'r') as file:
            data = json.load(file)
            data["history"] = add_history(data["history"], {"role": "user", "content": [{"text": content_message}]}) 
            save_history(session_id, data)  
            return data
    else:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
       
    
    
def get_intent(question):
    skills = ', '.join(SKILLS.keys())
    try:
        response = client.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=[{"role": "user", "content": [{"text": question}]}],
            system=[{"text": f"You are an intent classifier. Classify the user message into exactly one of these intents: {skills}. Use 'support' if the user wants to create, submit, log, or raise a ticket or report an issue. Use 'documentation' for all other questions about HR policies, leave, payroll, benefits, onboarding, or any information lookup. Reply with only the intent name, nothing else."}],
        )
        return response["output"]["message"]["content"][0]["text"].strip().lower()
    except ClientError as exc:
        raise translate_client_error(exc) from exc