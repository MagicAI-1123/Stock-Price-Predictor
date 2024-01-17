from fastapi import APIRouter, Depends, Form
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.Dependency.Auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from app.Models.Auth import Token
from app.Models.User import User, add_user, get_all_users, SignInModel, UserForClient, SignUpModel, find_user_by_email

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
    if user.password != user.confirm_password:
        raise ValueError("The two passwords did not match.")
    
    hashed_password = get_password_hash(user.password)
    user.email = user.email.lower()
    user_in_db = find_user_by_email(user.email)
    if not user_in_db:
        # new_user = User(email=user.email, hashed_password=hashed_password)
        new_user = {"email": user.email, "hashed_password": hashed_password}
        print("type: ", type(new_user))
        user_id = add_user(new_user)
        print("new_user: ", new_user)
        access_token = create_access_token(data={"sub": new_user["email"]})
        return {"access_token": access_token, "token_type": "bearer", "user": User(**new_user)}
    else:
        return "That email alrealy exist"

@router.post("/get-me/")
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    return UserForClient(**user.dict())

@router.post("/get-user-list/")
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    users = get_all_users()
    return users