"""Middleware to set the user's language based on their setting."""

from django.utils import translation


class UserLanguageMiddleware:
    """Represent middleware to set the user's language based on their setting."""

    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """Set the user's language based on their setting."""
        if request.user.is_authenticated:
            translation.activate(request.user.language)
            request.LANGUAGE_CODE = request.user.language
        response = self.get_response(request)
        translation.deactivate()
        return response
