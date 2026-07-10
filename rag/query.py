import boto3
import json
import chromadb
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_ID = os.getenv("MODEL_ID")
client = chromadb.PersistentClient(path="/Users/appfire-nishthaarora/Documents/code/docs/nexus-hr-agent")
collection = client.get_collection("nexus_hr_docs")


def get_embedding(user_query):
    client = boto3.client("bedrock-runtime")
    response = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({
            'inputText': user_query
        })
    )
    return json.loads(response.get("body").read()).get("embedding")


def query_rag(embedded_query):
    results = collection.query(
        query_embeddings=[embedded_query],
        n_results=3,
        include=["distances", "documents"]
    )
    return results

def generate_response(user_query):
    client = boto3.client("bedrock-runtime")
    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'messages': [{ 'role': 'user', 'content': [{"type": "text", "text": user_query}] }],
            'max_tokens': 1024
        })
    )
    return json.loads(response.get("body").read())

def ask(question: str) -> str:
      embedded_query = get_embedding(question)
      results = query_rag(embedded_query)
      chunks = results['documents'][0]
      context = "\n\n".join(chunks)
      prompt = f"""Answer using this context:
      {context}
      question: {question}"""
      response = generate_response(prompt)
      return response['content'][0]['text']

if __name__ == "__main__":
    user_query = "How to onboard a customer?"
    embedded_query = get_embedding(user_query)
    results = query_rag(embedded_query)
    chunk = results['documents'][0]
    context = "\n\n".join(chunk)
    prompt = f"""Answer using this context:
    {context}
    question: {user_query}"""
    
    response = generate_response(prompt)
    print(response['content'][0]['text'])