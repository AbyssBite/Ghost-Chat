# from datetime import datetime, timedelta, timezone
# from typing import Annotated
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from jwt import PyJWTError
# import jwt
# from pwdlib import PasswordHash

# from app.schemas.token import Token, TokenData

# SECRET_KEY = "hwjX2TBqMgl2vu5dLQdLbT4qlPXvBp1aO2IbzX/3rBYNEwevu/jkmAIQk5AhFb+vFmHFvaSYI1A7ujDdOOFpTQ=="
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 15
# REFRESH_TOKEN_EXPIRE_DAYS = 7

# pwd_context = PasswordHash.recommended()
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# def create_access_token(data: dict, expires_delta: timedelta | None = None):
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + (
#         expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     )
#     to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="could not valiidate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_scopes = payload.get("scopes", [])
#         token_data = TokenData(sub=username, scopes=token_scopes)
#     except PyJWTError:
#         raise credentials_exception
