from pydantic import BaseModel
from typing import List
from app.Database import db

groupList_DB = db.newsGroup


# Define a Pydantic model for the items in the newsData array
class NewsItem(BaseModel):
    stockName: str
    headlineInfo: str

# Define a Pydantic model for the request body that includes the newsData array
class NewsDataArray(BaseModel):
    newsData: List[NewsItem]

class ConsensusModel(BaseModel):
    stockName: str

class ChartModel(ConsensusModel):
    start: str
    end: str

def find_all_groups():
    result = groupList_DB.find()
    all_groups = []
    for group in result:
        print(group)
        del group['_id']
        all_groups.append(group)
    return all_groups
