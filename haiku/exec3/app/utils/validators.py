import re

def is_valid_isbn(isbn: str) -> bool:
    isbn = isbn.replace("-", "").replace(" ", "")
    if len(isbn) not in [10, 13]:
        return False
    return isbn.isdigit()

def is_valid_username(username: str) -> bool:
    if len(username) < 3 or len(username) > 50:
        return False
    return re.match(r"^[a-zA-Z0-9_-]+$", username) is not None

def is_valid_password(password: str) -> bool:
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit

def is_valid_email(email: str) -> bool:
    if len(email) < 5 or len(email) > 100:
        return False
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None
