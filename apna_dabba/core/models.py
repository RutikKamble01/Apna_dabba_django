from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from django.core.exceptions import ValidationError


class TiffinService(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.name


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

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['price']

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

    class Meta:
        unique_together = ('menu', 'day')
        ordering = ['day']

    def __str__(self):
        return f"{self.menu.title} - {self.day}"


class CustomerSubscription(models.Model):
    """
    Tracks customer subscriptions with auto-expiry and business logic.
    """
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_subscriptions')
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    payment_status = models.CharField(max_length=20, default="Paid")

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        # Prevent duplicate active subscriptions per customer per menu
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'menu'],
                condition=models.Q(is_active=True),
                name='unique_active_subscription_per_customer_menu'
            )
        ]

    def clean(self):
        """Validate that only one active subscription exists per customer per menu."""
        if self.is_active:
            existing = CustomerSubscription.objects.filter(
                customer=self.customer,
                menu=self.menu,
                is_active=True
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    f"Customer already has an active subscription for {self.menu.title}"
                )

    def save(self, *args, **kwargs):
        """Override save to enforce business rules."""
        # Set end_date if not provided
        if not self.end_date:
            self.end_date = timezone.now() + timedelta(
                days=self.subscription.duration_in_days
            )
        
        # Auto-expiry check: deactivate if end_date has passed
        if self.is_active and timezone.now() > self.end_date:
            self.is_active = False
        
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        """Calculate days remaining in subscription."""
        if not self.is_active:
            return 0
        remaining = (self.end_date.date() - date.today()).days
        return max(0, remaining)

    @property
    def status(self):
        """Get human-readable status."""
        if not self.is_active:
            return "Expired"
        if self.days_remaining == 0:
            return "Expiring Today"
        if self.days_remaining <= 7:
            return "Expiring Soon"
        return "Active"

    def extend_by_days(self, days=1):
        """Extend subscription end date (used for skip extension)."""
        self.end_date += timedelta(days=days)
        self.save()

    def __str__(self):
        return f"{self.customer.username} - {self.subscription.title}"


class DailyMealTracking(models.Model):
    """
    Tracks daily meal status (Taken/Skipped) for subscriptions.
    """
    STATUS_CHOICES = [
        ('Taken', 'Taken'),
        ('Skipped', 'Skipped'),
    ]

    subscription = models.ForeignKey(
        'CustomerSubscription',
        on_delete=models.CASCADE,
        related_name="daily_tracking"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Taken')
    
    # Legacy field for backward compatibility
    taken = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('subscription', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['subscription', 'date']),
        ]

    def save(self, *args, **kwargs):
        """Sync taken field with status."""
        self.taken = (self.status == 'Taken')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subscription.customer.username} - {self.date} - {self.status}"
