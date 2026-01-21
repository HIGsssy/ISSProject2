"""
Middleware to capture the current user for audit logging.
"""
import threading

_thread_locals = threading.local()


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    """Set the current user in thread-local storage."""
    _thread_locals.user = user


class AuditUserMiddleware:
    """
    Middleware to store the current user in thread-local storage.
    This allows signals to access the user who made the change.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store user before processing request
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            set_current_user(user)
        else:
            set_current_user(None)
        
        response = self.get_response(request)
        
        # Clean up after request
        set_current_user(None)
        
        return response
