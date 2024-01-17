from pydantic import BaseModel
from typing import List

class FavouriteData(BaseModel):  # Pydantic model representing the favourite data structure
    name: str
    email: str
    sources: List[str]
    date: str

class RequestFavourite(BaseModel):
    name: str
    sources: List[str]