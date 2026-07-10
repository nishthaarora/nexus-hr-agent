import json
from rag.agent import run_agent
import uuid
from rag.skills import SKILLS
from dotenv import load_dotenv
import boto3
import time

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

def judge(answer, expected):
    client = boto3.client("bedrock-runtime")

    if expected == "NOT_IN_DOCS":
        system_prompt = "The expected answer is NOT_IN_DOCS meaning the agent should say it does not have the information. Reply PASS if the agent says it doesn't know or can't find the information, FAIL otherwise."
    else:
        system_prompt = "You are an eval judge. Reply PASS if the actual answer conveys the same key information as the expected answer, even if worded differently. Reply FAIL if key information is missing or wrong. Reply with only PASS or FAIL."

    response = client.converse(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{
            "role": "user",
            "content": [{"text": f"Expected: {expected}\nActual: {answer}"}],
        }],
        system=[{"text": system_prompt}]
    )

    return response["output"]["message"]["content"][0]["text"].strip()


with open('evals/golden_dataset.json', 'r') as file:
    golden_dataset = json.load(file)

total = len(golden_dataset["questions"])
passed = 0
failed = 0

print(f"\n{BOLD}{'═' * 60}{RESET}")
print(f"{BOLD}  Nexus HR Copilot — Evaluation Suite{RESET}")
print(f"{BOLD}{'═' * 60}{RESET}")
print(f"{DIM}  Running {total} test cases...{RESET}\n")

for i, question in enumerate(golden_dataset["questions"], 1):
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "intent": question["intent"],
        "tools": SKILLS[question["intent"]]["tools"],
        "system_prompt": SKILLS[question["intent"]]["system_prompt"],
        "history": [{"role": "user", "content": [{"text": question["question"]}]}]
    }

    print(f"{BOLD}[{i}/{total}]{RESET} {question['question']}")
    print(f"{DIM}  Intent: {question['intent']}{RESET}")

    answer = run_agent(session)
    answer_text = answer["content"][0]["text"]

    print(f"{DIM}  Agent: {answer_text[:120]}{'...' if len(answer_text) > 120 else ''}{RESET}")

    result = judge(answer_text, question["expected"])

    if "PASS" in result.upper():
        passed += 1
        print(f"  {GREEN}{BOLD}✓ PASS{RESET}")
    else:
        failed += 1
        print(f"  {RED}{BOLD}✗ FAIL{RESET}")

    print()

pass_rate = round((passed / total) * 100)

print(f"{BOLD}{'═' * 60}{RESET}")
print(f"{BOLD}  Results{RESET}")
print(f"{'─' * 60}")
print(f"  Total:   {total}")
print(f"  {GREEN}Passed:  {passed}{RESET}")
print(f"  {RED}Failed:  {failed}{RESET}")
print(f"  Score:   {GREEN if pass_rate >= 80 else YELLOW if pass_rate >= 60 else RED}{pass_rate}%{RESET}")
print(f"{BOLD}{'═' * 60}{RESET}\n")
