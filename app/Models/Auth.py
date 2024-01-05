from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    tokey_type: str


class TokenData(BaseModel):
    username: str | None = None