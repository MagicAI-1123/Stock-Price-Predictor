from pydantic import BaseModel
from app.Database import db
from typing import List
from bson import json_util
from bson.objectid import ObjectId
from datetime import date, datetime

ChatlogsDB = db.chatlogs


class Message(BaseModel):
    content: str
    role: str
    date: datetime = datetime.now()


class ChatlogIdModel(BaseModel):
    logId: str


class Chatlog(BaseModel):
    logId: str
    createdDate: datetime = datetime.now()
    messages: List[Message] = []


def find_all_chatlogs(email: str):
    result = ChatlogsDB.find({"logId": 1, "createdDate": 1})
    all_logs = []
    for log in result:
        print(log)
        log["_id"] = str(log["_id"])
        all_logs.append(log)
    return all_logs


def find_messages_by_id(logId: str):
    result = ChatlogsDB.find_one({"logId": logId})
    if result == None:
        return []
    return Chatlog(**result).messages

def remove_chatlog(id: str, email: str):
    ChatlogsDB.delete_one({"logId": id, "email": email})
    return True



def add_new_message(logId: str, msg: Message):
    result = ChatlogsDB.find_one({"logId": logId})

    if result:
        # If row with logId exists, append the new message to the existing messages list
        ChatlogsDB.update_one({"logId": logId}, {
            "$push": {
                "messages": msg.dict()
            }
        })

    else:
        # If row with logId doesn't exist, create a new Chatlog object and save it to the database
        new_chatlog = Chatlog(
            logId=logId,
            messages=[msg]
        )
        ChatlogsDB.insert_one(new_chatlog.dict())
