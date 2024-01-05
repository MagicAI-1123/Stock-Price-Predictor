from fastapi import FastAPI, Form
import app.Routers.Chatbot as Chatbot
import app.Routers.Auth as auth

import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import openai
import json
from app.Models.News import NewsDataArray
from app.Utils.DB import generate_news_hash
from app.Database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Chatbot.router, tags=["Chatbot"])
app.include_router(auth.router, tags=['Auth'], prefix="/auth")


@app.get("/")
async def root():
    return {"message": "Hello World"}


###########################################################


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7000, reload=True)
