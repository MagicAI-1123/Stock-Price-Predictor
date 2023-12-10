from pydantic import BaseModel
from typing import List

# Define a Pydantic model for the items in the newsData array
class NewsItem(BaseModel):
    # Replace these fields with the actual structure of your news item
    stockName: str
    headlineInfo: str

# Define a Pydantic model for the request body that includes the newsData array
class NewsDataArray(BaseModel):
    newsData: List[NewsItem]