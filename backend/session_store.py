
import os
import json
import boto3
from dotenv import load_dotenv
from rag.skills import SKILLS
load_dotenv()

client = boto3.client("bedrock-runtime")

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
    response = client.converse(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": [{"text": question}]}],
        system=[{"text": f"Classify the intent as one of these skills: {skills}. Reply with only the skill name."}],
    )
    return response["output"]["message"]["content"][0]["text"]
