from fastapi import FastAPI, Form
import app.Routers.Chatbot as Chatbot
import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import openai
import json
from app.Models.News import NewsDataArray
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Chatbot.router, tags=["Chatbot"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

###########################################################

@app.post("/headline-analysis/")
async def headline_analysis(stockData: NewsDataArray):

    output_data = {
        "status": "success",  # Default status
        "stockData": ""
    }
    stockData = stockData["newsData"]

    api_key = os.getenv('OPENAI_API_KEY')
    MODEL = "gpt-4-1106-preview"
    openai.api_key = api_key
    
    # Convert stockData into the required format
    for item in stockData:
        prompt1 = f"""
        You're an investor. I'll give you a headline from a company {item['stockName']}. You just answer is this news positive or negative or neutral for the price of the stock as a one word. choices: Positive, Negative, Neutral.
                """
        prompt2 = f"""
        Here is a headline from a company {item['stockName']}. Would an investor consider this news more positive or more negative for the price of the stock. Explain in detail. 60 words
                """    
        try:
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt1},
                    {"role": "user", "content": str(item['headlineInfo'])}
                ],
                temperature=0,
            )
            status = response['choices'][0]['message']['content']

            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt2},
                    {"role": "user", "content": str(item['headlineInfo'])}
                ],
                temperature=0,
            )
            detail = response['choices'][0]['message']['content']
            item['status'] = status
            item['detail'] = detail
        except Exception as e:
            output_data["status"] = str(e)  # Store the error message

    output_data["stockData"] = stockData
    return output_data

@app.get("/latest-news/")
async def get_latest_news():

    return "hello world"

###########################################################


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7000, reload=True)
