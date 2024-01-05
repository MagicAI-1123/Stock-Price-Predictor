from fastapi import APIRouter, Depends, Form
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.Dependency.Auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from app.Models.Auth import Token
from app.Models.User import User, add_user, get_all_users, SignInModel, UserForClient, SignUpModel

router = APIRouter()

@router.post("/sign-in")
def login_for_access_token(data: SignInModel):
    user = authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/sign-up")
def sign_up(user: SignUpModel):
    user_model = User(**user.dict())
    user_model.password = get_password_hash(user_model.password)
    user_model.email = user_model.email.lower()
    add_user(user_model)
    return True

@router.post("/get-me/")
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    return UserForClient(**user.dict())

@router.post("/get-user-list/")
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    users = get_all_users()
    return users