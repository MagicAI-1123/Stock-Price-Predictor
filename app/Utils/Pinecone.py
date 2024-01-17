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
import json
import sys
from datetime import datetime, timedelta

from app.Database import db
latest_News_DB = db.latestNews
old_News_DB = db.stockNews

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
count = 0

def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

def split_document(doc: Document):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        length_function=tiktoken_len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents([doc])
    print(len(chunks))
    return chunks


def train_stock(news: object, namespace: str):
    start_time = time.time()
    print(news["detail"])
    print(tiktoken_len(news["detail"]))
    news_dump = json.dumps(news)
    doc = Document(page_content=news["headlineInfo"], metadata={"source": news_dump})
    chunks = split_document(doc)
    Pinecone.from_documents(
        chunks, embeddings, index_name=index_name, namespace=namespace)

    doc = Document(page_content=news["detail"], metadata={"source": news_dump})
    chunks = split_document(doc)
    Pinecone.from_documents(
        chunks, embeddings, index_name=index_name, namespace=namespace)

    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)

def get_context(query_str: str, namespace: str):
    context = ""
    print("query : " + query_str)
    print(namespace)

    # db = Pinecone.from_existing_index(
    #     index_name=index_name, namespace=namespace, embedding=embeddings)

    response = openai.Embedding.create(
        input=query_str,
        model="text-embedding-ada-002"
    )
    query_embedding = response['data'][0]['embedding']
    index = pinecone.Index(index_name)
    # print(query_embedding)

    results = index.query(
        vector=query_embedding,
        top_k=10,
        include_metadata=True,
        namespace=namespace
    )
    # print(results['matches'])
    # context = results['matches']
    for result in results['matches']:
        context += result.metadata['news'] + '\n'
    print("context: ", context)
    return context   


def get_answer(msg: str, log_id:str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    pinecone_context = f"""
        Today is {date_str}.
    """
    # print(log_id)
    for days in range(0, 7):
        now = datetime.now()
        date_only = (now - timedelta(days=days)).date()
        date_str = date_only.strftime("%Y-%m-%d")
        days_context = get_context(msg, date_str)
        pinecone_context += f"""
            - This is the news from {days} days ago that you can refer to.
            {days_context}
        """
    
    old_context = get_context(msg, "old")
    pinecone_context += f"""
        - This news was published more than a week ago that you can refer to.
        {old_context}
    """
    print(pinecone_context)

    print(tiktoken_len(pinecone_context))

    instructor = f"""
        You will act as a kind Stock news analyser and assistant for stocks.
        Below is the list of latest headlines for stocks.
        Each item contains headline and matching stock names.
        You can refer to this context.
        -----------------------
        {pinecone_context}
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
        # print(response)
        print(final)
    except Exception as e:
        print(e)

    add_new_message_to_db(logId=log_id, msg=Message(content=msg, role="user"))
    add_new_message_to_db(logId=log_id, msg=Message(content=final, role="assistant"))

    # return final

def estimate_time_difference(given_date):
    now = datetime.now().date()
    difference = now - given_date
    return difference.days


def embed_into_index(contexts_to_embed, metadatas, namespace: str):
    global count
    try:
        # Ensure that contexts_to_embed is a list of strings and not empty
        if isinstance(contexts_to_embed, list) and all(isinstance(item, str) for item in contexts_to_embed):
            response = openai.Embedding.create(
                input=contexts_to_embed,
                model="text-embedding-ada-002"
            )
            embeddings = [embedding['embedding'] for embedding in response['data']]

            # Initialize Pinecone index
            index = pinecone.Index(index_name)
            
            # Prepare the vectors for upserting to Pinecone
            vectors = []
            for embedding, metadata in zip(embeddings, metadatas):
                vectors.append({
                    "id": "vec" + str(count),
                    'values': embedding,
                    "metadata": {"news": metadata}
                })
                count += 1
            
            # Upsert the vectors to Pinecone
            upsert_response = index.upsert(
                vectors=vectors,
                namespace=namespace
            )
        else:
            print("Error: 'contexts_to_embed' is empty or contains non-string elements.")
    except openai.error.InvalidRequestError as e:
        print("Invalid request to OpenAI API:")
        print(e)
    except Exception as e:
        print("An error occurred while processing embeddings or upserting to Pinecone:")
        print(e)
    

def get_size(obj, seen=None):
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def train_latest_news():
    latest_news = latest_News_DB.find({}, {'_id': 0})

    contexts_to_embed = []
    metadata = []
    total_tokens = 0
    start_time = time.time()
    max_message_size = 4194304 * 0.9
    news_dump = ""
    for news in latest_news:
        # print(news)
        news_dump = None
        if 'headlineInfo' in news and news['headlineInfo'] is not None:
            contexts_to_embed.append(news['headlineInfo'])
            total_tokens += tiktoken_len(news['headlineInfo'])
            news_dump = news['headlineInfo']
            metadata.append(news_dump)
        if 'detail' in news and news['detail'] is not None:
            contexts_to_embed.append(news['detail'])
            total_tokens += tiktoken_len(news['detail'])
            if news_dump is not None:
                metadata.append(news_dump)
        
        # Check the size before adding more data
        current_size = get_size(contexts_to_embed) + get_size(metadata)
        if current_size >= max_message_size or total_tokens > 7500 :
            # if 'date' not in news:
            #     print(news)
            # print(type(news['date']))
            

            if isinstance(news['date'], str):
                namespace, time_str = news['date'].split()
            else:
                namespace = namespace = news['date'].strftime("%Y-%m-%d")
                print(namespace)

            embed_into_index(contexts_to_embed, metadata, namespace)
            print(len(contexts_to_embed))
            total_tokens = 0
            contexts_to_embed = []
            metadata = []
    if len(contexts_to_embed) > 0:
        embed_into_index(contexts_to_embed, metadata, namespace)

def train_old_news():
    # old_news = old_News_DB.find({})
    # contexts_to_embed = []
    # for news in old_news:
    #     news.pop('_id', None)
    #     news.pop('date', None)
    #     contexts_to_embed.append(news["headlineInfo"])

    old_news_cursor = old_News_DB.find({}, {'date': 0, '_id': 0})

    contexts_to_embed = []
    metadata = []
    total_tokens = 0
    start_time = time.time()
    max_message_size = 4194304 * 0.9
    news_dump = ""
    
    for news in old_news_cursor:
        news_dump = None
        if 'headlineInfo' in news and news['headlineInfo'] is not None:
            contexts_to_embed.append(news['headlineInfo'])
            total_tokens += tiktoken_len(news['headlineInfo'])
            news_dump = news['headlineInfo']
            metadata.append(news_dump)
        if 'detail' in news and news['detail'] is not None:
            contexts_to_embed.append(news['detail'])
            total_tokens += tiktoken_len(news['detail'])
            if news_dump is not None:
                metadata.append(news_dump)
        
        # Check the size before adding more data
        current_size = get_size(contexts_to_embed) + get_size(metadata)
        if current_size >= max_message_size or total_tokens > 7500 :
            embed_into_index(contexts_to_embed, metadata, "old")
            print(len(contexts_to_embed))
            # print(total_tokens)
            # print(current_size)
            total_tokens = 0
            contexts_to_embed = []
            metadata = []
            # break
    if len(contexts_to_embed) > 0:
        embed_into_index(contexts_to_embed, metadata, "old")
    
    