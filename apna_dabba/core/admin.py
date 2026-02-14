from django.contrib import admin
from .models import TiffinService, Menu, Order, Review
from .models import Menu

# admin.site.register(Menu)
from .models import Subscription
admin.site.register(Subscription)


@admin.register(TiffinService)
class TiffinServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'phone', 'is_verified')
    list_filter = ('is_verified',)
    search_fields = ('name', 'owner__username')


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('title', 'tiffin_service', 'monthly_price')
    list_filter = ('tiffin_service',)
    search_fields = ('title',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('user__username',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'tiffin_service', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'tiffin_service__name')




# Register your models here.
