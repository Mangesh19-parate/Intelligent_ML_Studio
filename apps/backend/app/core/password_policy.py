"""
Canonical Password Policy for Intelligent ML Studio.
Enforces consistent password complexity rules across Auth and Admin modules.
"""

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> str:
    """
    Validates password length and complexity.
    Requires:
    - At least 8 characters
    - At most 128 characters
    - Must not be whitespace only
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password cannot exceed {MAX_PASSWORD_LENGTH} characters.")
    if not password.strip():
        raise ValueError("Password cannot consist solely of whitespace.")
    return password
