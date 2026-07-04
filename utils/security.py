# utils/security.py
import hashlib

def hash_password(password: str) -> str:
    """Превращает строку пароля в безопасный необратимый шестнадцатеричный хеш SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()