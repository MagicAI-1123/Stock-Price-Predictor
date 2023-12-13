import shutil
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Body
from typing import Annotated
import os
from app.Database import db
from bson import ObjectId, Regex
from fastapi.encoders import jsonable_encoder

router = APIRouter()
latest_DB = db.latestNews

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



@router.get("/get-stock-table")
async def get_stock_table(perPage: int = 10, currentPage: int = 1, searchText: str = '', filterStatus: str = ''):
    # Create a regex filter for the searchText
    search_filter = Regex(searchText, 'i')  # 'i' for case-insensitive

    # Define the fields to search in
    search_fields = ['date', 'stockName', 'stockDetail', 'headlineInfo', 'source', 'url', 'detail']

    # Create the query to filter documents containing the searchText in any of the search fields
    search_query = {
        '$or': [{field: search_filter} for field in search_fields]
    }

    # Create a filter for the status
    status_filter = {'status': filterStatus} if filterStatus else {}

    # Combine the search query with the status filter
    query = {
        '$and': [
            search_query,
            status_filter
        ]
    }

    # Calculate the total count of documents matching the search criteria
    totalCount = latest_DB.count_documents(query)

    # Calculate the range for pagination
    skip = perPage * (currentPage - 1)
    limit = perPage

    # Fetch the filtered and paginated data from the database
    cursor = latest_DB.find(query).skip(skip).limit(limit)
    
    # Convert the cursor to a list
    data_for_show = list(cursor)

    # Remove the '_id' field from the documents
    for document in data_for_show:
        document.pop('_id', None)

    # Return the JSON-encoded response including data_for_show and totalCount
    return jsonable_encoder({"data": data_for_show, "totalCount": totalCount})


@router.get("/get-number-data")
async def get_number_data(stockName: str = Form(...)):

    numberData_collection = db.numberData
    document = numberData_collection.find_one()

    return jsonable_encoder(document[stockName])


@router.get("/get-tickers")
async def get_tickers():

    tickers_collection = db.tickers
    document = tickers_collection.find_one()

    return jsonable_encoder(list(document["tickers"]))