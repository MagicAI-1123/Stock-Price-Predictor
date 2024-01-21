import shutil
import json
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Body, Query
from typing import Annotated, List
import os
import pytz
from app.Database import db
from bson import ObjectId, Regex
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
from app.Utils.Pinecone import get_answer, train_latest_news, train_old_news
from app.Models.User import User, QuestionModel, find_user_by_email
from app.Models.ChatLogModel import find_messages_by_id
from app.Models.Favourite import FavouriteData, RequestFavourite
from app.Models.News import ChartModel, ConsensusModel, find_all_groups
from app.Dependency.Auth import get_current_user
from app.Utils.News import chart_data, up_downgrades_consensus

from fastapi.responses import StreamingResponse
router = APIRouter()
latest_DB = db.stockNews
favourites_DB = db.favourites
# groupList_DB = db.


def fix_object_id(data):
    if isinstance(data, list):
        return [fix_object_id(item) for item in data]
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            else:
                data[key] = fix_object_id(value)
    return data


@router.get("/unique-sources")
async def get_unique_sources():
    try:
        # Use the distinct method to get all unique values for the 'source' field
        unique_sources = latest_DB.distinct("source")
        return {"sources": unique_sources}
    except Exception as e:
        # In case of any errors, return an HTTP 500 error with the exception message
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-stock-table")
async def get_stock_table(perPage: int = 10, currentPage: int = 1, searchText: str = '', filterStatus: str = '', startDate: str = datetime.now().strftime("%Y-%m-%d"), endDate: str = datetime.now().strftime("%Y-%m-%d"), filterSource: List[str] = Query(None), timezone: str = "America/New_York"):

    if (timezone == "undefined"):
        timezone = "America/New_York"
    # Convert the startDate and endDate to the timezone specified
    tz = pytz.timezone(timezone)
    start_date = tz.localize(datetime.strptime(startDate, "%Y-%m-%d"))
    end_date = tz.localize(datetime.strptime(
        endDate, "%Y-%m-%d")) + timedelta(days=1)  # Include the entire endDate

    # Split the searchText into individual search terms and strip whitespace
    search_terms = [term.strip()
                    for term in searchText.split(',') if term.strip()]

    # Create a regex filter for each search term (case-insensitive)
    search_filters = [Regex(term, 'i') for term in search_terms]
    print(search_filters)
    # Define the fields to search in
    search_fields = ['date', 'stockName', 'stockDetail',
                     'headlineInfo', 'source', 'url', 'detail']

    

    # Create the query to filter documents containing any of the search terms in any of the search fields
    search_query = {
        '$or': [{field: {'$in': search_filters}} for field in search_fields]
    } if search_terms else {}
    
    # Create a filter for the status

    # Parse date strings into datetime objects and create a date range filter
    date_filter = {}
    if startDate and endDate:
        start_date = datetime.strptime(startDate, "%Y-%m-%d")
        # Add 1 day to include the entire endDate
        end_date = datetime.strptime(endDate, "%Y-%m-%d") + timedelta(days=1)
        # Use $lt to exclude the next day
        date_filter = {'date': {'$gte': start_date, '$lt': end_date}}

    # Check if filterSource is not empty and contains a single string element
    if filterSource and len(filterSource) == 1 and isinstance(filterSource[0], str):
        try:
            # Decode the JSON string to get a list of sources
            actual_filterSource_list = json.loads(filterSource[0])
        except json.JSONDecodeError:
            # Handle the case where the JSON decoding fails
            actual_filterSource_list = []
    else:
        # If filterSource is not in the expected format, treat it as an empty list
        actual_filterSource_list = []

    # Now create the source filter using the decoded list, if it's not empty
    source_filter = {'source': {'$in': actual_filterSource_list}
                     } if actual_filterSource_list else None

    status_count_to_return = {"all": 0, "Positive": 0, "Negative": 0, "Neutral": 0}
    status_list = ["", "Positive", "Negative", "Neutral"]
    status_count_list = []
    for status in status_list:
        status_filter = {'status': status} if status else {}
        query_filters = [f for f in (
            search_query, status_filter, date_filter, source_filter) if f]
        # Combine all filters, excluding any that are None or empty dictionaries
        query = {'$and': query_filters} if query_filters else {}
        status_count_list.append(latest_DB.count_documents(query))
    print(status_count_list)

    status_count_to_return = dict(zip(status_count_to_return.keys(), status_count_list))
    print(status_count_to_return)


    status_filter = {'status': filterStatus} if filterStatus else {}
    query_filters = [f for f in (
        search_query, status_filter, date_filter, source_filter) if f]
    # Combine all filters, excluding any that are None or empty dictionaries
    query = {'$and': query_filters} if query_filters else {}

    # Calculate the range for pagination
    skip = perPage * (currentPage - 1)
    limit = perPage

    # Fetch the filtered and paginated data from the database
    cursor = latest_DB.find(query).sort('date', -1).skip(skip).limit(limit)

    # Convert the cursor to a list
    data_for_show = list(cursor)

    # When returning the data, convert the 'date' of each document to the specified timezone
    for document in data_for_show:
        document.pop('_id', None)
        # Convert the 'date' field to the specified timezone
        if 'date' in document:
            # Assume 'date' is already a datetime object
            local_date = document['date'].replace(
                tzinfo=pytz.utc).astimezone(tz)
            document['date'] = local_date.strftime("%Y-%m-%d %H:%M:%S")

    # Return the JSON-encoded response including data_for_show and totalCount
    return jsonable_encoder({"data": data_for_show, **status_count_to_return})


@router.get("/get-number-data")
async def get_number_data(stockName: str):
    numberData_collection = db.numberData
    document = numberData_collection.find_one()

    return jsonable_encoder(document[stockName])


@router.get("/get-stock-headlines")
async def get_stock_headlines(stockName: str):
    # Calculate the date 7 days ago from today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Create a query to filter by stockName and date range
    query = {
        'stockName': stockName,
        'date': {'$gte': start_date, '$lt': end_date}
    }

    # Fetch the filtered data from the database and sort by date in descending order
    cursor = latest_DB.find(query).sort('date', -1)

    # Convert the cursor to a list
    data_for_show = list(cursor)

    # Remove the '_id' field from the documents
    for document in data_for_show:
        document.pop('_id', None)

    # Return the JSON-encoded response including data_for_show
    return jsonable_encoder({"data": data_for_show})


@router.get("/get-tickers")
async def get_tickers():

    tickers_collection = db.tickers
    document = tickers_collection.find_one()

    return jsonable_encoder(list(document["tickers"]))


@router.post("/user-question")
def ask_question(question: QuestionModel): #user: Annotated[User, Depends(get_current_user)], 
# def ask_question(user: Annotated[User, Depends(get_current_user)], msg: str = Form(...)):
    # print(msg)
    try:
        # print(user.email)
        # print(get_user_id(user.email))
        
        saved_messages = find_messages_by_id(user.email)
        saved_messages = find_messages_by_id("goldrace@gmail.com")
        if len(saved_messages) >= 20:
            print("exceed")
            return "you exceeded daily limit"
        return StreamingResponse(get_answer(question.msg, user.email), media_type='text/event-stream')
        # return StreamingResponse(get_answer(question.msg, "goldrace@gmail.com"), media_type='text/event-stream')
    except Exception as e:
        print(e)
        return e

@router.post("/find-all-chatlogs")
def find_all_chatlogs(user: Annotated[User, Depends(get_current_user)]):
    try:
        return find_messages_by_id(user.email)
    except Exception as e:
        print(e)
        return e

@router.post("/embbed-latest-news")
def embbed_latest_news():
    try:
        print("embbed latest")
        train_latest_news()
    except Exception as e:
        print(e)
        return e


@router.post("/embbed-old-news")
def embbed_old_news():
    try:
        print("embbed old")
        train_old_news()
    except Exception as e:
        print(e)
        return e


@router.post("/save-favourite")
# 
async def save_favourite(user: Annotated[User, Depends(get_current_user)], data: RequestFavourite):
    favourite_data = {
        "name": data.name,
        "email": "user.email",
        "sources": data.sources,
        "date": datetime.now().strftime("%d/%m/%Y")
    }
    # Insert the favourite data into the database
    insert_result = favourites_DB.insert_one(favourite_data)
    if insert_result.inserted_id:
        return {"status": "success", "message": "Favourite saved successfully"}
    else:
        raise HTTPException(
            status_code=500, detail="Failed to save favourite data")


@router.get("/get-favourite")
async def get_favourite(user: Annotated[User, Depends(get_current_user)]):
    # Find the favourite data for the current user using their email
    favourite_data = favourites_DB.find({"email": "user.email"})
    favourites_list = list(favourite_data)

    # Convert the '_id' field to a string for each document
    for favourite in favourites_list:
        favourite['_id'] = str(favourite['_id'])
    return jsonable_encoder(favourites_list)



@router.post("/get-chart-data")
def get_chart_data(user: Annotated[User, Depends(get_current_user)], chartdata: ChartModel):
    try:
        return chart_data(chartdata.stockName, chartdata.start, chartdata.end)
    except Exception as e:
        print(e)
        return e

@router.post("/send-mail")
async def send_mail(user: Annotated[User, Depends(get_current_user)]):
    try:
        from_email_obj = Email(from_mail)  # Change to your verified sender
        to_email_obj = To(user.email)  # Change to your recipient
        # text = f""
        subject = "phone verification"
        content = Content("text/plain", text)
        mail = Mail(from_email_obj, to_email_obj, subject, content)

        # Get a JSON-ready representation of the Mail object
        mail_json = mail.get()

        # Send an HTTP POST request to /mail/send
        response = sendgrid_client.client.mail.send.post(
            request_body=mail_json)
        if response.status_code == 202:
            return True
        else:
            return False
    except Exception as e:
        print(f"Send mail Error: {e}")
        # return HTTPException(status_code=500, detail={"error": e})
        return False

@router.get("/email-verification")
def email_verification(user: Annotated[User, Depends(get_current_user)]):
    return True


@router.post("/up-downgrades")
def up_downgrades(user: Annotated[User, Depends(get_current_user)], data: ConsensusModel):
    try:
        return up_downgrades_consensus(data.stockName)
    except Exception as e:
        print(e)
        return e

@router.post("/get-grouplist")
def get_grouplist(user: Annotated[User, Depends(get_current_user)]):
    try:
        return find_all_groups()
    except Exception as e:
        print(e)
        return e
    