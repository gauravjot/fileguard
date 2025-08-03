from datetime import timedelta
from django.db import models
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.timezone import now
import hashlib
from secrets import token_urlsafe


class SessionManager(models.Manager):
    """Manages the session
    - Create a session: Key generation and expiry
    - Delete a session: Invalidating sessions
    - Get a session: Retrieve a session by key, or id
    """

    def __init__(self):
        super().__init__()
        # Session expiry in days
        self.KEY_EXPIRE_IN_SECONDS = 3600 * 24 * 7  # 7 days

    def create_session(self, request):
        """Primary use case: Create a session on signup/login

        Args:
                user (User): User to create session for
                request (HttpRequest): For IP and User-Agent

        Returns:
                tuple(key: str, session: Session)
        """
        # Disable previous sessions
        self.filter(is_valid=True).update(is_valid=False)
        # Create a new session
        key = token_urlsafe(64)
        session = self.create(
            key=hash_this(key),
            expire_at=now() + timedelta(seconds=self.KEY_EXPIRE_IN_SECONDS)
        )
        return urlsafe_base64_encode(key.encode("ascii")), session

    def delete_session(self, session_id):
        """Primary use case: Logout

        Args:
                session_id (uuid): The row id of the session
        """
        try:
            session = self.get(pk=session_id, is_valid=True)
            if session.is_valid:
                session.is_valid = False
                session.updated_at = now()
                session.save()
                return True
        except Exception as e:
            return False
        return False

    def authenticate_session(self, key):
        """This function authenticates a user request

        Args:
                key (str): Session key

        Returns:
                Session or None
        """
        try:
            key = urlsafe_base64_decode(key).decode("ascii")
            session = self.get(
                key=hash_this(key),
                is_valid=True
            )
            if session.expire_at < now():
                session.is_valid = False
                session.updated_at = now()
                session.save()
                return None
            return session
        except Exception as e:
            return None

    def get_session_if_valid(self, session_id):
        """Get session if it is valid and not expired.

        Args:
                user (User): User model object
                session_id (int): Session row id

        Returns:
                Session or None
        """
        try:
            session = self.get(
                pk=session_id,
                is_valid=True
            )
            if session.expire_at < now():
                session.is_valid = False
                session.save()
                return None
            return session
        except Exception as e:
            return None

    def get_last_session(self):
        return self.order_by('-created_at').first()


def hash_this(string):
    return hashlib.sha256(str(string).encode('utf-8')).hexdigest()
