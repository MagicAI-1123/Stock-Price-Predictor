import shutil
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Body
from typing import Annotated
import os
from app.Database import db
from bson import ObjectId
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
async def get_stock_table():

    cursor = latest_DB.find({})
    data_for_show = []
    
    for document in cursor:
        document.pop('_id')
        data_for_show.append(document)

    return jsonable_encoder(data_for_show)


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