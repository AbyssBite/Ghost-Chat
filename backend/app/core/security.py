from pwdlib import PasswordHash

pwd_context = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return pwd_context.hash(password=password)


def verify_password(plain_passwod: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_passwod, hashed_password)
