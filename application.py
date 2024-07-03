import os
import re
import time
import json
import logging
import requests
from typing import Optional, Any, Dict
from fastapi import FastAPI, Depends, HTTPException, Body, Request, APIRouter

from utils import motive_test

app = FastAPI()

@app.get("/_meta/")
async def root():
    return {
        "response": "hello"
    }

@app.on_event("startup")
async def startup_event():
    motive_test.initialize_db()

@app.post("/ask/")
async def ask(request: Request) -> Dict[str, Any]:
    data = await request.json()
    question = data.get('question')
    chat_context = data.get('chat_context')
    
    answer = motive_test.execute_graph(
        question,
        chat_context
    )
    
    return {
        "response": answer
    }