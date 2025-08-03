from typing import Optional
from .models import Session


def _auth_using_cookies(request) -> Optional[Session]:
    session = None
    # Check if auth token is present in cookies
    try:
        key = request.COOKIES.get('fileguard_session')
        session = Session.manage.authenticate_session(key)
        return session
    except (KeyError, Exception) as e:
        session = None
    return session


class ActiveUserMiddleware:
    """
    This reads the Cookie or Authorization header and authenticates the user.
    For Cookie-based authentication, `request.active_session` gets be attached to the request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = _auth_using_cookies(request)
        # Attach the session to the request
        request.active_session = session

        response = self.get_response(request)
        return response
