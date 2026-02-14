"""
Custom decorators for role-based access control.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def owner_required(view_func):
    """
    Decorator to ensure only owners (is_staff=True) can access a view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('login')
        
        if not request.user.is_staff:
            messages.error(request, "Access denied. Owner privileges required.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def customer_required(view_func):
    """
    Decorator to ensure only customers (is_staff=False) can access a view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('login')
        
        if request.user.is_staff:
            messages.error(request, "Access denied. Customer access only.")
            return redirect('owner_dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
