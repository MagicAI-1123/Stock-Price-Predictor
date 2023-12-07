from fastapi import FastAPI, Form
import app.Routers.Chatbot as Chatbot
import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import openai

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

@app.get("/headline-analysis/")
async def headline_analysis(stockName: str = Form(...), headlineInfo: str = Form(...)):

    input_data = {
        "stockName": stockName,
        "headlineInfo": headlineInfo
    }

    output_data = {
        "status": "error",  # Default status
        "message": "",
        "analysis": {}
    }

    api_key = os.getenv('OPENAI_API_KEY')
    MODEL = "gpt-4"
    prompt1 = f"""
    You're an investor. I'll give you a headline from a company {stockName}. You just answer is this news positive or negative or neutral for the price of the stock as a one word. choices: Positive, Negative, Neutral.
            """
    prompt2 = f"""
    Here is a headline from a company {stockName}. Would an investor consider this news more positive or more negative for the price of the stock. Explain in detail. 60 words
            """
    
    openai.api_key = api_key
    
    try:
        response1 = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt1},
                {"role": "user", "content": input_data["headlineInfo"]}
            ],
            temperature=0,
        )
        output_data["analysis"]["status"] = response1['choices'][0]['message']['content']

        response2 = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt2},
                {"role": "user", "content": input_data["headlineInfo"]}
            ],
            temperature=0,
        )
        output_data["analysis"]["detail"] = response2['choices'][0]['message']['content']
        
        output_data["status"] = "success"  # Update status to success if no exception occurred

    except Exception as e:
        output_data["message"] = str(e)  # Store the error message

    return output_data


@app.get("/latest-news/")
async def get_latest_news():

    return "hellow world"

###########################################################


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7000, reload=True)
