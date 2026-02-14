"""
Business logic utilities for Apna Dabba SaaS system.
"""
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from decimal import Decimal
from .models import CustomerSubscription, DailyMealTracking


def deactivate_expired_subscriptions():
    """
    Auto-expiry rule: Deactivate subscriptions where end_date has passed.
    This should be called periodically (via middleware or cron).
    """
    expired_count = CustomerSubscription.objects.filter(
        end_date__lt=timezone.now(),
        is_active=True
    ).update(is_active=False)
    
    return expired_count


def handle_payment_success(customer, subscription):
    """
    Rule 1: On Payment Success
    - Create CustomerSubscription
    - start_date = today
    - end_date = today + duration_days
    - is_active = True
    
    Returns: CustomerSubscription instance or None if duplicate exists
    """
    # Prevent duplicate active subscription
    existing = CustomerSubscription.objects.filter(
        customer=customer,
        menu=subscription.menu,
        is_active=True
    ).first()
    
    if existing:
        return None  # Already subscribed
    
    # Deactivate any other active subscriptions for this customer+menu
    CustomerSubscription.objects.filter(
        customer=customer,
        menu=subscription.menu,
        is_active=True
    ).update(is_active=True)
    
    # Create new subscription
    customer_subscription = CustomerSubscription.objects.create(
        customer=customer,
        subscription=subscription,
        menu=subscription.menu,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=subscription.duration_in_days),
        is_active=True,
        payment_status="Paid"
    )
    
    return customer_subscription


def handle_skip_extension(customer_subscription, tracking_date=None):
    """
    Rule 2: Skip Extension
    - If status = Skipped: extend end_date by 1 day
    
    Args:
        customer_subscription: CustomerSubscription instance
        tracking_date: Date to mark as skipped (defaults to today)
    """
    if tracking_date is None:
        tracking_date = date.today()
    
    # Create or update tracking entry
    tracking, created = DailyMealTracking.objects.get_or_create(
        subscription=customer_subscription,
        date=tracking_date,
        defaults={'status': 'Skipped', 'taken': False}
    )
    
    # If marking as skipped for first time, extend subscription
    if created and tracking.status == 'Skipped':
        customer_subscription.extend_by_days(1)
    
    # If updating existing entry to skipped, extend
    elif tracking.status != 'Skipped':
        tracking.status = 'Skipped'
        tracking.taken = False
        tracking.save()
        customer_subscription.extend_by_days(1)
    
    return tracking


def calculate_owner_revenue(owner):
    """
    Calculate revenue metrics for owner dashboard.
    
    Returns dict with:
    - total_revenue: Sum of all active subscription prices
    - monthly_revenue: Revenue from subscriptions created this month
    - active_subscribers: Count of active subscriptions
    - total_menus: Count of menus owned
    """
    from .models import Menu
    
    # Get owner's menus
    menus = Menu.objects.filter(tiffin_service__owner=owner)
    
    # Get active subscriptions for owner's menus
    active_subscriptions = CustomerSubscription.objects.filter(
        menu__tiffin_service__owner=owner,
        is_active=True
    )
    
    # Calculate total revenue (sum of subscription prices)
    total_revenue = active_subscriptions.aggregate(
        total=Sum('subscription__price')
    )['total'] or Decimal('0.00')
    
    # Calculate monthly revenue (subscriptions created this month)
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_subscriptions = CustomerSubscription.objects.filter(
        menu__tiffin_service__owner=owner,
        created_at__gte=current_month_start,
        is_active=True
    )
    monthly_revenue = monthly_subscriptions.aggregate(
        total=Sum('subscription__price')
    )['total'] or Decimal('0.00')
    
    # Count active subscribers (unique customers)
    active_subscribers = active_subscriptions.values('customer').distinct().count()
    
    # Count total menus
    total_menus = menus.count()
    
    return {
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'active_subscribers': active_subscribers,
        'total_menus': total_menus,
    }


def get_customer_dashboard_stats(customer):
    """
    Get statistics for customer dashboard.
    
    Returns dict with:
    - active_subscriptions: QuerySet of active subscriptions
    - total_subscriptions: Count of all subscriptions
    - days_remaining: Days remaining in primary subscription
    """
    active_subscriptions = CustomerSubscription.objects.filter(
        customer=customer,
        is_active=True
    ).select_related('subscription', 'menu').order_by('-created_at')
    
    primary_subscription = active_subscriptions.first()
    
    return {
        'active_subscriptions': active_subscriptions,
        'total_subscriptions': CustomerSubscription.objects.filter(
            customer=customer
        ).count(),
        'primary_subscription': primary_subscription,
        'days_remaining': primary_subscription.days_remaining if primary_subscription else 0,
    }
