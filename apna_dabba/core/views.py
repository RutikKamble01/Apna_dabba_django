"""
Enhanced views with business logic, security, and SaaS-level features.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta

from .models import (
    Menu, TiffinService, Subscription, DailyMenu,
    CustomerSubscription, DailyMealTracking, Order, Review
)
from .utils import (
    handle_payment_success,
    handle_skip_extension,
    calculate_owner_revenue,
    get_customer_dashboard_stats,
)
from .decorators import owner_required, customer_required


# ==================== PUBLIC VIEWS ====================

def home(request):
    """Home page with role-based content."""
    owner_menus = None
    customer_menus = None
    active_subscriptions = None

    if request.user.is_authenticated:
        if request.user.is_staff:
            owner_menus = Menu.objects.filter(
                tiffin_service__owner=request.user
            ).select_related('tiffin_service')
        else:
            customer_menus = Menu.objects.all()[:6]  # Show limited menus
            active_subscriptions = CustomerSubscription.objects.filter(
                customer=request.user,
                is_active=True
            ).select_related('subscription', 'menu')

    return render(request, "core/home.html", {
        "owner_menus": owner_menus,
        "customer_menus": customer_menus,
        "active_subscriptions": active_subscriptions
    })


def login_page(request):
    """Login page with role-based redirect."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('owner_dashboard')
        return redirect('customer_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role', 'customer')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Verify role matches
            if role == 'owner' and not user.is_staff:
                messages.error(request, 'Invalid credentials for owner login.')
                return render(request, 'core/login.html', {'error': 'Invalid credentials'})
            elif role == 'customer' and user.is_staff:
                messages.error(request, 'Please use owner login.')
                return render(request, 'core/login.html', {'error': 'Please use owner login'})

            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')

            if user.is_staff:
                return redirect('owner_dashboard')
            else:
                return redirect('customer_dashboard')
        else:
            return render(request, 'core/login.html', {
                'error': 'Invalid username or password'
            })

    return render(request, 'core/login.html')


def register(request):
    """Customer registration."""
    if request.user.is_authenticated:
        return redirect('customer_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {
                'error': 'Username already exists'
            })

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=False
        )

        messages.success(request, 'Registration successful! Please login.')
        return redirect('login')

    return render(request, 'core/register.html')


def owner_register(request):
    """Owner registration."""
    if request.user.is_authenticated:
        return redirect('owner_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            return render(request, 'core/owner_register.html', {
                'error': 'Username already exists'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True
        )

        # Create TiffinService for owner
        TiffinService.objects.create(
            owner=user,
            name=username,
            address='Not Provided',
            phone='Not Provided'
        )

        messages.success(request, 'Owner registration successful! Please login.')
        return redirect('login')

    return render(request, 'core/owner_register.html')


def logout_user(request):
    """Logout user."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


# ==================== CUSTOMER VIEWS ====================

@login_required
@customer_required
def customer_dashboard(request):
    """Customer dashboard with subscription stats and calendar."""
    stats = get_customer_dashboard_stats(request.user)
    
    primary_subscription = stats['primary_subscription']
    grid_data = []
    
    if primary_subscription:
        # Generate calendar grid for last 30 days
        start_date = max(
            primary_subscription.start_date.date(),
            date.today() - timedelta(days=30)
        )
        today = date.today()
        
        current = start_date
        while current <= today:
            tracking = DailyMealTracking.objects.filter(
                subscription=primary_subscription,
                date=current
            ).first()
            
            grid_data.append({
                "date": current,
                "taken": tracking.taken if tracking else False,
                "status": tracking.status if tracking else None,
            })
            current += timedelta(days=1)
    
    # Get available menus
    menus = Menu.objects.all()[:6]
    
    return render(request, "core/customer_dashboard.html", {
        "active_subscriptions": stats['active_subscriptions'],
        "primary_subscription": primary_subscription,
        "days_remaining": stats['days_remaining'],
        "grid_data": grid_data,
        "menus": menus,
        "total_subscriptions": stats['total_subscriptions'],
    })


@login_required
@customer_required
def menu(request):
    """Menu browsing page for customers."""
    menus = Menu.objects.all().select_related('tiffin_service').prefetch_related('subscriptions')
    
    query = request.GET.get("q")
    if query:
        menus = menus.filter(Q(title__icontains=query) | Q(description__icontains=query))
    
    # Mark subscriptions as subscribed if customer has active subscription
    for menu in menus:
        for sub in menu.subscriptions.all():
            active = CustomerSubscription.objects.filter(
                customer=request.user,
                subscription=sub,
                is_active=True
            ).exists()
            sub.is_subscribed = active
    
    return render(request, "core/menu.html", {
        "menus": menus,
        "query": query,
        "is_customer": True,
    })


@login_required
@customer_required
def subscribe(request, subscription_id):
    """Initiate subscription (redirects to payment)."""
    subscription = get_object_or_404(Subscription, id=subscription_id)
    
    # Check if already subscribed
    already_subscribed = CustomerSubscription.objects.filter(
        customer=request.user,
        subscription=subscription,
        is_active=True
    ).exists()
    
    if already_subscribed:
        messages.warning(request, 'You already have an active subscription for this menu.')
        return redirect('menu')
    
    return redirect('payment_page', subscription_id=subscription.id)


@login_required
@customer_required
def payment_page(request, subscription_id):
    """Payment page with simulated payment processing."""
    subscription = get_object_or_404(Subscription, id=subscription_id)
    
    # Check if already subscribed
    existing = CustomerSubscription.objects.filter(
        customer=request.user,
        subscription=subscription,
        is_active=True
    ).first()
    
    if existing:
        messages.info(request, 'You already have an active subscription.')
        return redirect('customer_dashboard')
    
    if request.method == "POST":
        card = request.POST.get("card_number")
        expiry = request.POST.get("expiry")
        cvv = request.POST.get("cvv")
        
        if card and expiry and cvv:
            # Process payment using utility function
            customer_subscription = handle_payment_success(request.user, subscription)
            
            if customer_subscription:
                messages.success(
                    request,
                    f'Payment successful! Your subscription is active until {customer_subscription.end_date.strftime("%B %d, %Y")}.'
                )
                return redirect("customer_dashboard")
            else:
                messages.error(request, 'Subscription failed. You may already have an active subscription.')
        else:
            messages.error(request, 'Please fill all payment fields.')
    
    return render(request, "core/payment.html", {
        "subscription": subscription
    })


@login_required
@customer_required
def order(request):
    """Customer orders page."""
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'core/order.html', {'orders': orders})


# ==================== OWNER VIEWS ====================

@login_required
@owner_required
def owner_dashboard(request):
    """Owner dashboard with revenue aggregation and stats."""
    # Calculate revenue metrics
    revenue_stats = calculate_owner_revenue(request.user)
    
    # Get owner's menus
    menus = Menu.objects.filter(
        tiffin_service__owner=request.user
    ).select_related('tiffin_service')
    
    # Get active subscriptions for owner's menus
    subscriptions = CustomerSubscription.objects.filter(
        menu__tiffin_service__owner=request.user,
        is_active=True
    ).select_related('customer', 'subscription', 'menu').order_by('-created_at')
    
    return render(request, 'core/owner_dashboard.html', {
        'menus': menus,
        'subscriptions': subscriptions,
        'revenue_stats': revenue_stats,
    })


@login_required
@owner_required
def add_menu(request):
    """Add new menu (owner only)."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        
        tiffin_service, created = TiffinService.objects.get_or_create(
            owner=request.user,
            defaults={
                'name': request.user.username,
                'address': 'Not Provided',
                'phone': 'Not Provided'
            }
        )
        
        Menu.objects.create(
            tiffin_service=tiffin_service,
            title=title,
            description=description,
            monthly_price=price,
            image=image,
            monday=request.POST.get('monday', ''),
            tuesday=request.POST.get('tuesday', ''),
            wednesday=request.POST.get('wednesday', ''),
            thursday=request.POST.get('thursday', ''),
            friday=request.POST.get('friday', ''),
            saturday=request.POST.get('saturday', ''),
            sunday=request.POST.get('sunday', ''),
        )
        
        messages.success(request, f'Menu "{title}" added successfully!')
        return redirect('owner_dashboard')
    
    return render(request, 'core/add_menu.html')


@login_required
@owner_required
def edit_menu(request, menu_id):
    """Edit menu (owner only, with ownership validation)."""
    menu = get_object_or_404(Menu, id=menu_id)
    
    # Security: Verify ownership
    if menu.tiffin_service.owner != request.user:
        messages.error(request, 'Access denied. You do not own this menu.')
        return redirect('owner_dashboard')
    
    if request.method == "POST":
        menu.title = request.POST.get('title')
        menu.description = request.POST.get('description')
        menu.monthly_price = request.POST.get('monthly_price')
        
        if request.FILES.get('image'):
            menu.image = request.FILES.get('image')
        
        menu.save()
        messages.success(request, 'Menu updated successfully!')
        return redirect('owner_dashboard')
    
    return render(request, 'core/edit_menu.html', {'menu': menu})


@login_required
@owner_required
def delete_menu(request, menu_id):
    """Delete menu (owner only, with ownership validation)."""
    menu = get_object_or_404(Menu, id=menu_id)
    
    # Security: Verify ownership
    if menu.tiffin_service.owner != request.user:
        messages.error(request, 'Access denied. You do not own this menu.')
        return redirect('owner_dashboard')
    
    menu_title = menu.title
    menu.delete()
    messages.success(request, f'Menu "{menu_title}" deleted successfully!')
    return redirect('owner_dashboard')


@login_required
@owner_required
def add_subscription(request, menu_id):
    """Add subscription plan to menu (owner only)."""
    menu = get_object_or_404(Menu, id=menu_id)
    
    # Security: Verify ownership
    if menu.tiffin_service.owner != request.user:
        messages.error(request, 'Access denied. You do not own this menu.')
        return redirect('owner_dashboard')
    
    if request.method == 'POST':
        Subscription.objects.create(
            menu=menu,
            title=request.POST.get('title'),
            duration_in_days=request.POST.get('duration'),
            price=request.POST.get('price'),
            description=request.POST.get('description', '')
        )
        messages.success(request, 'Subscription plan added successfully!')
        return redirect('owner_dashboard')
    
    return render(request, 'core/add_subscription.html', {'menu': menu})


@login_required
@owner_required
def select_menu_for_subscription(request):
    """Select menu to add subscription plan."""
    menus = Menu.objects.filter(
        tiffin_service__owner=request.user
    ).select_related('tiffin_service')
    
    return render(
        request,
        'core/select_menu_for_subscription.html',
        {'menus': menus}
    )


@login_required
@owner_required
def add_daily_menu(request, menu_id):
    """Add daily menu (owner only)."""
    menu = get_object_or_404(Menu, id=menu_id)
    
    # Security: Verify ownership
    if menu.tiffin_service.owner != request.user:
        messages.error(request, 'Access denied. You do not own this menu.')
        return redirect('owner_dashboard')
    
    if request.method == "POST":
        day = request.POST.get('day')
        food_description = request.POST.get('food_description')
        image = request.FILES.get('image')
        
        DailyMenu.objects.update_or_create(
            menu=menu,
            day=day,
            defaults={
                'food_description': food_description,
                'image': image
            }
        )
        
        messages.success(request, f'Daily menu for {day} updated successfully!')
        return redirect('owner_dashboard')
    
    return render(request, 'core/add_daily_menu.html', {'menu': menu})


@login_required
@owner_required
def toggle_meal_status(request, subscription_id):
    """Toggle meal status (Taken/Skipped) with skip extension logic."""
    subscription = get_object_or_404(CustomerSubscription, id=subscription_id)
    
    # Security: Verify ownership
    if subscription.menu.tiffin_service.owner != request.user:
        messages.error(request, 'Access denied.')
        return redirect('owner_dashboard')
    
    today = date.today()
    
    # Use utility function for skip extension logic
    tracking = handle_skip_extension(subscription, today)
    
    # Toggle status
    if tracking.status == 'Taken':
        tracking.status = 'Skipped'
        tracking.taken = False
    else:
        tracking.status = 'Taken'
        tracking.taken = True
    
    tracking.save()
    
    status_text = "marked as taken" if tracking.taken else "marked as skipped (subscription extended)"
    messages.success(request, f'Meal for {subscription.customer.username} {status_text}.')
    
    return redirect('owner_dashboard')


@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on role."""
    if request.user.is_staff:
        return redirect('owner_dashboard')
    else:
        return redirect('customer_dashboard')


# ==================== PUBLIC VIEWS ====================

def reviews(request):
    """Public reviews page."""
    reviews_list = Review.objects.all().select_related('user', 'tiffin_service').order_by('-created_at')[:10]
    return render(request, 'core/reviews.html', {'reviews': reviews_list})
