"""
Middleware for business logic automation.
"""
from .utils import deactivate_expired_subscriptions


class SubscriptionExpiryMiddleware:
    """
    Automatically deactivate expired subscriptions on each request.
    This ensures subscriptions are always up-to-date.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Run auto-expiry check before processing request
        deactivate_expired_subscriptions()
        
        response = self.get_response(request)
        return response
