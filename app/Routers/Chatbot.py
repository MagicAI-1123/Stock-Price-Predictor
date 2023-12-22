import shutil
import json
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Body, Query
from typing import Annotated, List
import os
from app.Database import db
from bson import ObjectId, Regex
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
router = APIRouter()
latest_DB = db.stockNews

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
async def get_stock_table(perPage: int = 10, currentPage: int = 1, searchText: str = '', filterStatus: str = '', startDate: str = datetime.now().strftime("%Y-%m-%d"), endDate: str = datetime.now().strftime("%Y-%m-%d"), filterSource: List[str] = Query(None)):
    # Split the searchText into individual search terms and strip whitespace
    search_terms = [term.strip() for term in searchText.split(',') if term.strip()]

    # Create a regex filter for each search term (case-insensitive)
    search_filters = [Regex(term, 'i') for term in search_terms]

    # Define the fields to search in
    search_fields = ['date', 'stockName', 'stockDetail', 'headlineInfo', 'source', 'url', 'detail']

    # Create the query to filter documents containing any of the search terms in any of the search fields
    search_query = {
        '$or': [{field: {'$in': search_filters}} for field in search_fields]
    } if search_terms else {}

    # Create a filter for the status
    status_filter = {'status': filterStatus} if filterStatus else {}

    # Parse date strings into datetime objects and create a date range filter
    date_filter = {}
    if startDate and endDate:
        start_date = datetime.strptime(startDate, "%Y-%m-%d")
        end_date = datetime.strptime(endDate, "%Y-%m-%d") + timedelta(days=1)  # Add 1 day to include the entire endDate
        date_filter = {'date': {'$gte': start_date, '$lt': end_date}}  # Use $lt to exclude the next day

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
    source_filter = {'source': {'$in': actual_filterSource_list}} if actual_filterSource_list else None

    # Combine all filters, excluding any that are None or empty dictionaries
    query_filters = [f for f in (search_query, status_filter, date_filter, source_filter) if f]

    query = {'$and': query_filters} if query_filters else {}
    # Calculate the total count of documents matching the search criteria
    totalCount = latest_DB.count_documents(query)

    # Calculate the range for pagination
    skip = perPage * (currentPage - 1)
    limit = perPage

    # Fetch the filtered and paginated data from the database
    cursor = latest_DB.find(query).sort('date', -1).skip(skip).limit(limit)
    
    # Convert the cursor to a list
    data_for_show = list(cursor)

    # Remove the '_id' field from the documents
    for document in data_for_show:
        document.pop('_id', None)

    # Return the JSON-encoded response including data_for_show and totalCount
    return jsonable_encoder({"data": data_for_show, "totalCount": totalCount})

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