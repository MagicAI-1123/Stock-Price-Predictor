from langchain.schema import Document
import pandas as pd
from fastapi import UploadFile, File
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import CSVLoader, PyPDFLoader, TextLoader, Docx2txtLoader
# from app.Utils.web_scraping import extract_content_from_url
# from app.Models.ChatbotModel import Chatbot
from app.Models.ChatLogModel import Message, add_new_message as add_new_message_to_db, find_messages_by_id
# from app.Models.SampleAnswerModel import SampleAnswer
from dotenv import load_dotenv
import os
import pinecone
import openai
import tiktoken
import time


from app.Database import db
latest_News_DB = db.latestNews

# from pinecone import Index

load_dotenv()
tokenizer = tiktoken.get_encoding('cl100k_base')

api_key = os.getenv('PINECONE_API_KEY')

pinecone.init(
    api_key=api_key,  # find at app.pinecone.io
    environment=os.getenv('PINECONE_ENV'),  # next to api key in console
)

index_name = os.getenv('PINECONE_INDEX')
embeddings = OpenAIEmbeddings()


def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

def get_context(query_str: str):

    print("query : " + query_str)
    
    best_match_ids = []
    best_match_result = []
    similarity_value_limit = 0.8

    db = Pinecone.from_existing_index(
        index_name=index_name, embedding=embeddings)
    results = db.similarity_search_with_score(query_str, k=20)

    for result in results:
        print("row_id: ", result[0].metadata['row_id'], ", score: ", result[1])
        best_match_ids.append(result[0].metadata['row_id'])
        best_match_result.append({"content":result[0].page_content})
        # if result[1] >= similarity_value_limit:
        #     matching_metadata.append(result[0].metadata['source'])
        #     context += f"\n\n{result[0].page_content}"

    # matching_metadata = list(set(matching_metadata))

    return best_match_result   


def get_answer(msg: str, log_id:str):
    pinecone_context = get_context(msg)
    print(pinecone_context)

    context = ""
    latest_news = latest_News_DB.find({})
    for news in latest_news:
        context += f"""
            [
            stock name: {news['stockName']}
            headline: {news["headlineInfo"]}
            date: {news["date"]}
            ]
            -------------------

        """
    print(tiktoken_len(context))

    instructor = f"""
        You will act as a kind Stock news analyser and assistant for stocks.
        Below is the list of latest headlines for stocks.
        Each item contains headline and matching stock names.
        You can refer to this context.
        -----------------------
        {context}
    """
    # instructor = f"""
    #     You will play the role of a stock headline analyst.
    # """
    # prompt = """
        # This article is about a company listed in the U.S. stock market and is intended to make the reader feel there is new information in this headline that would encourage the reader to either buy or sell the stock. Which would you recommend?
    # """
    # prompt = """
    #     Please read the following headline and determine what company (or companies) is the article about, and comment if the headline is intended for the reader to feel more positive or less positive about the stock price of the company.
    #     If you do not see the story as particularly convincing say the article is neutral.
    # """
    final = ""
    saved_messages = find_messages_by_id(log_id)
    messages = [{'role': message.role, 'content': message.content}
                for message in saved_messages[-4:]]
    messages.append({'role': 'user', 'content': msg + "\n Please answer based on given context."})
    messages.insert(0, {'role': 'system', 'content': instructor})
    # print(messages)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            max_tokens=3000,
            messages=messages,
            stream=True
        )
        for chunk in response:
            if 'content' in chunk.choices[0].delta:
                string = chunk.choices[0].delta.content
                yield string
                final += string
        # final = response_text = response['choices'][0]['message']['content']
        print(response)
        print(final)
    except Exception as e:
        print(e)

    add_new_message_to_db(logId=log_id, msg=Message(content=msg, role="user"))
    add_new_message_to_db(logId=log_id, msg=Message(content=final, role="assistant"))

    # print(response)
    # print(response.choices[0].message.content)
    return final
