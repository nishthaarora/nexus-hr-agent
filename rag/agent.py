from rag.tools import create_ticket, search_docs
import boto3
from dotenv import load_dotenv
import os

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
MODEL_ID = os.getenv("MODEL_ID")

    
MAX_RECURSIONS = 5
class UserAgentTool:
    def __init__(self):
         # Create a Bedrock Runtime client in the specified AWS Region.
        self.bedrockRuntimeClient = boto3.client(
            "bedrock-runtime", region_name=AWS_REGION
        )
    
    def run(self, session: dict):
        conversation = session["history"]
        tools = session["tools"]
        system_prompt = session["system_prompt"]

        # Send the conversation to Amazon Bedrock
        bedrock_response = self._send_conversation_to_bedrock(conversation, tools, system_prompt)
        print("bedrock_response", bedrock_response)
        # Recursively handle the model's response until the model has returned
        # its final response or the recursion counter has reached 0
        return self._process_model_response(
            bedrock_response, conversation, tools, system_prompt, max_recursion=MAX_RECURSIONS
        )


    def _send_conversation_to_bedrock(self, conversation, tools, system_prompt):
        return self.bedrockRuntimeClient.converse(
            modelId=MODEL_ID,
            messages=conversation,
            system=[{"text": system_prompt}],
            toolConfig={"tools": tools},
        )
    
    def _process_model_response(self, bedrock_response, conversation, tools, system_prompt, max_recursion):
        if max_recursion <= 0:
            return
        else:
            stop_reason = bedrock_response["stopReason"]
            if stop_reason == "tool_use":
                
                content = bedrock_response["output"]["message"]["content"]
                tool_use = next((item["toolUse"] for item in content if "toolUse" in item), None)
                
                if tool_use:
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]
                    if tool_name == "create_ticket":
                        tool_response = create_ticket(**tool_input)
                    elif tool_name == "search_docs":
                        tool_response = search_docs(**tool_input)
                else:
                    return bedrock_response["output"]["message"]["content"][0]["text"]
                    
                conversation.append(bedrock_response["output"]["message"])
                conversation.append({
                    "role": "user",
                    "content": [{"toolResult": {"toolUseId":
                tool_use["toolUseId"], "content": [{"text":
                str(tool_response)}]}}]
                })
                final_response = self._send_conversation_to_bedrock(conversation, tools, system_prompt)
                return self._process_model_response(final_response, conversation, tools, system_prompt, max_recursion - 1)
            else:
                return bedrock_response["output"]["message"]

    
def run_agent(session: dict) -> str:
    agent = UserAgentTool()
    return agent.run(session)

     
if __name__ == "__main__":
    tool_use_demo = UserAgentTool()
    tool_use_demo.run()
    