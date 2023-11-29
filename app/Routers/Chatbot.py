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



@router.post("/get-stock-table")
def get_stock_table():
  print("here")
  result = latest_DB.find_one({"stockName": "BA"})
  if result:
      result = fix_object_id(result)
  print(result)
  return jsonable_encoder(result)
