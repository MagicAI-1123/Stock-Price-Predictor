from pydantic import BaseModel, validator
from app.Database import db

UserDB = db.users


class UserForClient(BaseModel):
    email: str | None = None


class User(UserForClient):
    password: str


class UserWithAPI(User):
    api_key: dict


class SignInModel(BaseModel):
    email: str | None = None
    password: str


class SignUpModel(User):
    def password_match(cls, confirm_password, values):
        if 'password' in values and confirm_password != values['password']:
            raise ValueError("Passwords do not match")
        return confirm_password


def find_user_by_email(email: str):
    return UserDB.find_one({"email": email})


def add_user(user: User):
    return UserDB.insert_one(user.dict())


def get_all_users():
    users = list(user.find())
    return users
