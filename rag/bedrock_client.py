import os
from functools import lru_cache

import boto3
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION"))
