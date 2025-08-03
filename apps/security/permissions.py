from functools import wraps
from django.shortcuts import redirect


def is_authenticated():
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            session = request.active_session
            if session and session.is_valid:
                return func(request, *args, **kwargs)
            else:
                return redirect('security:login')
        return wrapper
    return decorator
