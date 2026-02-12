from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', views.login_page, name='login'),
    path('register/', views.register, name='register'),
    path('owner-register/', views.owner_register, name='owner_register'),

    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('owner-dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('subscribe/<int:subscription_id>/', views.subscribe, name='subscribe'),
    path('payment/<int:subscription_id>/', views.payment_page, name='payment_page'),



    path('menu/', views.menu, name='menu'),
    path('order/', views.order, name='order'),
    path('reviews/', views.reviews, name='reviews'),
    path('logout/', views.logout_user, name='logout'),
    path('add-menu/', views.add_menu, name='add_menu'),
    path('edit-menu/<int:menu_id>/', views.edit_menu, name='edit_menu'),
    path('delete-menu/<int:menu_id>/', views.delete_menu, name='delete_menu'),
    path('add-subscription/<int:menu_id>/', views.add_subscription, name='add_subscription'),
    path(
    'select-menu-for-subscription/',
    views.select_menu_for_subscription,
    name='select_menu_for_subscription'
),
    path('add-daily-menu/<int:menu_id>/', views.add_daily_menu, name='add_daily_menu'),





]
