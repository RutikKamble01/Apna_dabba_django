from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class TiffinService(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.name


from django.db import models

class Menu(models.Model):
    tiffin_service = models.ForeignKey(TiffinService, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    monthly_price = models.DecimalField(max_digits=7, decimal_places=2)
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True)

    monday = models.TextField(blank=True)
    tuesday = models.TextField(blank=True)
    wednesday = models.TextField(blank=True)
    thursday = models.TextField(blank=True)
    friday = models.TextField(blank=True)
    saturday = models.TextField(blank=True)
    sunday = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Delivered', 'Delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    address = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.menu.title}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tiffin_service = models.ForeignKey(TiffinService, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating}⭐"
    

class Subscription(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='subscriptions')
    title = models.CharField(max_length=100)
    duration_in_days = models.IntegerField()
    price = models.DecimalField(max_digits=7, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.menu.title}"


class DailyMenu(models.Model):
    DAYS = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='daily_menus')
    day = models.CharField(max_length=10, choices=DAYS)
    food_description = models.TextField()
    image = models.ImageField(upload_to='daily_menu_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.menu.title} - {self.day}"
    

from django.utils import timezone
from datetime import timedelta

class CustomerSubscription(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    payment_status = models.CharField(max_length=20, default="Paid")

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = timezone.now() + timedelta(
                days=self.subscription.duration_in_days
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.username} - {self.subscription.title}"

