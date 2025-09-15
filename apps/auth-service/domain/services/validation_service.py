"""Domain validation service"""

import re

from domain.errors import MissingRequiredFieldError, ValidationError


class ValidationService:
    """Domain validation service for auth operations"""

    # Email regex pattern (basic but practical)
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128

    @classmethod
    def validate_email(cls, email: str | None) -> str:
        """Validate email address"""
        if not email:
            raise MissingRequiredFieldError("email")

        email = email.strip().lower()
        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email address format")

        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long")

        return email

    @classmethod
    def validate_password(cls, password: str | None) -> str:
        """Validate password"""
        if not password:
            raise MissingRequiredFieldError("password")

        if len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long")

        if len(password) > cls.MAX_PASSWORD_LENGTH:
            raise ValidationError(f"Password must be less than {cls.MAX_PASSWORD_LENGTH} characters")

        return password

    @classmethod
    def validate_user_id(cls, user_id: str | None) -> str:
        """Validate user ID"""
        if not user_id:
            raise MissingRequiredFieldError("user_id")

        user_id = user_id.strip()
        if not user_id:
            raise ValidationError("User ID cannot be empty")

        return user_id

    @classmethod
    def validate_session_id(cls, session_id: str | None) -> str:
        """Validate session ID"""
        if not session_id:
            raise MissingRequiredFieldError("session_id")

        session_id = session_id.strip()
        if not session_id:
            raise ValidationError("Session ID cannot be empty")

        return session_id

    @classmethod
    def validate_name(cls, name: str | None, field_name: str) -> str | None:
        """Validate name fields (given_name, family_name)"""
        if not name:
            return None

        name = name.strip()
        if not name:
            return None

        if len(name) > 100:
            raise ValidationError(f"{field_name} must be less than 100 characters")

        return name

    @classmethod
    def validate_phone_number(cls, phone: str | None) -> str | None:
        """Validate phone number"""
        if not phone:
            return None

        phone = phone.strip()
        if not phone:
            return None

        # Basic phone validation - starts with + and contains only digits, spaces, hyphens
        phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        clean_phone = re.sub(r"[\s\-\(\)]", "", phone)

        if not phone_pattern.match(clean_phone):
            raise ValidationError("Invalid phone number format")

        return phone

    @classmethod
    def validate_oauth_code(cls, code: str | None) -> str:
        """Validate OAuth authorization code"""
        if not code:
            raise MissingRequiredFieldError("authorization_code")

        code = code.strip()
        if not code:
            raise ValidationError("Authorization code cannot be empty")

        return code

    @classmethod
    def validate_redirect_uri(cls, uri: str | None) -> str:
        """Validate OAuth redirect URI"""
        if not uri:
            raise MissingRequiredFieldError("redirect_uri")

        uri = uri.strip()
        if not uri:
            raise ValidationError("Redirect URI cannot be empty")

        # Basic URI validation
        if not (uri.startswith("http://") or uri.startswith("https://")):
            raise ValidationError("Redirect URI must use HTTP or HTTPS")

        return uri

    @classmethod
    def validate_confirmation_code(cls, code: str | None) -> str:
        """Validate confirmation code"""
        if not code:
            raise MissingRequiredFieldError("confirmation_code")

        code = code.strip()
        if not code:
            raise ValidationError("Confirmation code cannot be empty")

        if len(code) < 4 or len(code) > 10:
            raise ValidationError("Confirmation code must be between 4 and 10 characters")

        return code

    @classmethod
    def validate_required_fields(cls, data: dict, required_fields: list[str]) -> None:
        """Validate that all required fields are present"""
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    @classmethod
    def sanitize_user_input(cls, value: str | None) -> str | None:
        """Sanitize user input"""
        if not value:
            return None

        # Strip whitespace and normalize
        value = value.strip()
        if not value:
            return None

        # Remove any null bytes or control characters
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)

        return value if value else None
