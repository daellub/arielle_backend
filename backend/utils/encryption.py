# backend/utils/encryption.py

from dotenv import load_dotenv
import os
from cryptography.fernet import Fernet

load_dotenv()

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY').encode()

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY가 설정되어 있지 않습니다!")

fernet = Fernet(ENCRYPTION_KEY)

def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()