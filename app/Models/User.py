from pydantic import BaseModel, validator
from app.Database import db

UserDB = db.users


class UserForClient(BaseModel):
    email: str | None = None


class User(UserForClient):
    hashed_password: str



class UserWithAPI(User):
    api_key: dict


class SignInModel(BaseModel):
    email: str | None = None
    password: str


class SignUpModel(SignInModel):
    confirm_password: str

class QuestionModel(BaseModel):
    msg: str


def find_user_by_email(email: str):
    user = UserDB.find_one({"email": email})
    if not user:
        return None
    return User(**user)

# def get_user_id(email: str):
#     user = UserDB.find_one({"email": email})
#     return str(user["_id"])

def add_user(user: User):
    return UserDB.insert_one(user)


def get_all_users():
    users = list(user.find())
    return users
