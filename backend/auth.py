from fastapi import Depends, Header, HTTPException
import os

API_KEY = os.getenv("NEXT_PUBLIC_API_KEY")


def require_api_key(x_api_key: str = Header(...)) -> None:
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
