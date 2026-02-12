
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Menu
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Menu, TiffinService
from django.shortcuts import get_object_or_404
from .models import Subscription
from .models import DailyMenu
from .models import Menu
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Menu, DailyMenu
from django.utils import timezone
from .models import CustomerSubscription
from datetime import timedelta
from django.contrib import messages





def home(request):

    owner_menus = None
    customer_menus = None
    active_subscriptions = None

    if request.user.is_authenticated:

        if request.user.is_staff:
            owner_menus = Menu.objects.filter(
                tiffin_service__owner=request.user
            )
        else:
            customer_menus = Menu.objects.all()

            active_subscriptions = CustomerSubscription.objects.filter(
                customer=request.user,
                is_active=True
            )

    return render(request, "core/home.html", {
        "owner_menus": owner_menus,
        "customer_menus": customer_menus,
        "active_subscriptions": active_subscriptions
    })


@login_required
def customer_dashboard(request):
    if request.user.is_staff:
        return redirect('home')

    deactivate_expired_subscriptions()

    menus = Menu.objects.all()

    active_subscriptions = CustomerSubscription.objects.filter(
        customer=request.user,
        is_active=True
    )

    return render(request, 'core/customer_dashboard.html', {
        'menus': menus,
        'active_subscriptions': active_subscriptions
    })

@login_required

def owner_dashboard(request):
    deactivate_expired_subscriptions()
    if not request.user.is_staff:
        return redirect('home')

    menus = Menu.objects.filter(tiffin_service__owner=request.user)

    subscriptions = CustomerSubscription.objects.filter(
        menu__tiffin_service__owner=request.user,
        is_active=True
    )

    return render(request, 'core/owner_dashboard.html', {
        'menus': menus,
        'subscriptions': subscriptions
    })


def logout_user(request):
    logout(request)
    return redirect('login')




def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # 🔁 Role-based redirect
            if user.is_staff:
                return redirect('home')

            else:
                return redirect('home')

        else:
            return render(request, 'core/login.html', {
                'error': 'Invalid username or password'
            })

    return render(request, 'core/login.html')




def register(request):
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
            is_staff=False   # Customer
        )

        # ✅ REDIRECT TO LOGIN
        return redirect('login')

    return render(request, 'core/register.html')



def owner_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            return render(request, 'core/owner_register.html', {
                'error': 'Username already exists'
            })

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True   # Owner
        )

        # ✅ REDIRECT TO LOGIN
        return redirect('login')

    return render(request, 'core/owner_register.html')



@login_required
def menu(request):
    deactivate_expired_subscriptions()

    if request.user.is_staff:
        menus = Menu.objects.filter(
            tiffin_service__owner=request.user
        )
    else:
        menus = Menu.objects.all()

    query = request.GET.get("q")
    if query:
        menus = menus.filter(title__icontains=query)

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
        "query": query
    })


@login_required
def order(request):
    if request.user.is_staff:
        return redirect('menu')   # owner blocked

    return render(request, 'core/order.html')


def reviews(request):
    return render(request, 'core/reviews.html')


def add_menu(request):
    

    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image = request.FILES.get('image')

        tiffin_service, created = TiffinService.objects.get_or_create(
    owner=request.user,
    defaults={
        'name': request.user.username,
        'address': 'Not Provided'
    }
)


        Menu.objects.create(
        tiffin_service=tiffin_service,
        title=title,
        description=description,
        monthly_price=price,
        image=image,
        monday=request.POST.get('monday'),
        tuesday=request.POST.get('tuesday'),
        wednesday=request.POST.get('wednesday'),
        thursday=request.POST.get('thursday'),
        friday=request.POST.get('friday'),
        saturday=request.POST.get('saturday'),
        sunday=request.POST.get('sunday'),
)


        return redirect('owner_dashboard')

    return render(request, 'core/add_menu.html')


@login_required
def edit_menu(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    # 🔐 SECURITY CHECK
    if not request.user.is_staff or menu.tiffin_service.owner != request.user:
        return redirect('menu')

    if request.method == "POST":
        menu.title = request.POST.get('title')
        menu.description = request.POST.get('description')
        menu.monthly_price = request.POST.get('monthly_price')

        if request.FILES.get('image'):
            menu.image = request.FILES.get('image')

        menu.save()
        return redirect('menu')

    return render(request, 'core/edit_menu.html', {'menu': menu})


@login_required
def delete_menu(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    # 🔐 SECURITY CHECK
    if not request.user.is_staff or menu.tiffin_service.owner != request.user:
        return redirect('menu')

    menu.delete()
    return redirect('menu')


def add_subscription(request, menu_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')

    menu = get_object_or_404(Menu, id=menu_id)

    # Ownership check
    if menu.tiffin_service.owner != request.user:
        return redirect('owner_dashboard')

    if request.method == 'POST':
        Subscription.objects.create(
            menu=menu,
            title=request.POST.get('title'),
            duration_in_days=request.POST.get('duration'),
            price=request.POST.get('price'),
            description=request.POST.get('description')
        )
        return redirect('menu')

    return render(request, 'core/add_subscription.html', {'menu': menu})

def select_menu_for_subscription(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')

    menus = Menu.objects.filter(
        tiffin_service__owner=request.user
    )

    return render(
        request,
        'core/select_menu_for_subscription.html',
        {'menus': menus}
    )

def add_daily_menu(request, menu_id):

    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == "POST":
        print("POST DATA:", request.POST)

        day = request.POST.get('day')
        food_description = request.POST.get('food_description')
        image = request.FILES.get('image')

        DailyMenu.objects.create(
            menu=menu,   # 🔥 THIS LINKS DAILY MENU TO MENU
            day=day,
            food_description=food_description,
            image=image
        )

        return redirect('menu')

    return render(request, 'core/add_daily_menu.html', {'menu': menu})

@login_required
def dashboard_redirect(request):
    if request.user.is_staff:
        return redirect('owner_dashboard')
    else:
        return redirect('customer_dashboard')
    
@login_required
def subscribe(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)

    if request.user.is_staff:
        return redirect('menu')

    # Check active subscription
    already_subscribed = CustomerSubscription.objects.filter(
        customer=request.user,
        subscription=subscription,
        is_active=True
    ).exists()

    if already_subscribed:
        return redirect('menu')

    # 🔥 REDIRECT TO PAYMENT PAGE
    return redirect('payment_page', subscription_id=subscription.id)



def deactivate_expired_subscriptions():
    from django.utils import timezone

    CustomerSubscription.objects.filter(
        end_date__lt=timezone.now(),
        is_active=True
    ).update(is_active=False)



@login_required
def payment_page(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)

    if request.method == "POST":

        # Fake payment validation
        card = request.POST.get("card_number")
        expiry = request.POST.get("expiry")
        cvv = request.POST.get("cvv")

        if card and expiry and cvv:

            # Prevent duplicate active subscription
            existing = CustomerSubscription.objects.filter(
                customer=request.user,
                subscription=subscription,
                is_active=True
            ).exists()

            if not existing:
                CustomerSubscription.objects.create(
                    customer=request.user,
                    subscription=subscription,
                    menu=subscription.menu,
                    is_active=True,
                    payment_status="Paid"
                )

            return redirect("menu")

    return render(request, "core/payment.html", {
        "subscription": subscription
    })

