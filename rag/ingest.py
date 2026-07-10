import os
import boto3
import chromadb
from dotenv import load_dotenv
from datetime import datetime
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid

load_dotenv()


client = chromadb.PersistentClient(path="/Users/appfire-nishthaarora/Documents/code/docs/nexus-hr-agent")
created_collection = client.get_or_create_collection(name="nexus_hr_docs", metadata={"created_at": datetime.now().isoformat()})

def chunk_text(text, chunk_size=500, overlap=10):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def embed_text(text):
    client = boto3.client("bedrock-runtime")
    response = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({
            'inputText': text
        })
    )
    return json.loads(response.get("body").read()).get("embedding")
    
def ingest_file(filepath):
   with open(filepath) as f:
    text = f.read()
    chunks = chunk_text(text)
    for chunk in chunks:
        embedding = embed_text(chunk)
        created_collection.add(embeddings=embedding, documents=[chunk], ids=[str(uuid.uuid4())])
    print(f"Chunked {len(chunks)} chunks")



if __name__ == "__main__":
    docs_dir = "docs"
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(docs_dir, filename)
            ingest_file(filepath)
            print(f"Ingested {filename}")
    print("done")