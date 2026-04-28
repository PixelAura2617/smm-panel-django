from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random


# 🔹 SERVICES
class Service(models.Model):
    name = models.CharField(max_length=200)
    provider_service_id = models.IntegerField()

    cost_price = models.FloatField()
    margin_percent = models.FloatField(default=30)
    category = models.CharField(max_length=100, default="Genral")

    min_qty = models.IntegerField(default=1)
    max_qty = models.IntegerField(default=1000000)

    @property
    def price(self):
        return round(self.cost_price + (self.cost_price * self.margin_percent / 100), 2)

    def __str__(self):
        return f"{self.name} ({self.category})"


# 🔹 PROFILE (BALANCE + REFERRAL)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.FloatField(default=0)

    referral_code = models.CharField(max_length=10, unique=True, blank=True)
    referred_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals'
    )

    is_reseller = models.BooleanField(default=False)
    reseller_margin = models.FloatField(default=10)

    def __str__(self):
        return f"{self.user.username} - ₹{self.balance}"

    def generate_referral_code(self):
        return str(random.randint(100000, 999999))

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = self.generate_referral_code()

            # 🔥 ensure unique
            while Profile.objects.filter(referral_code=code).exists():
                code = self.generate_referral_code()

            self.referral_code = code

        super().save(*args, **kwargs)


# 🔹 AUTO CREATE PROFILE
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# 🔹 ORDERS
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    link = models.URLField()
    quantity = models.IntegerField()

    price = models.FloatField()
    profit = models.FloatField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_order_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.service.name} - {self.quantity} - {self.status}"


# 🔹 TRANSACTIONS (PAYMENT + REFERRAL)
class Transaction(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('referral', 'Referral Bonus'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.status}"
    
class WithdrawRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.FloatField()
    upi_id = models.CharField(max_length=100)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.status}"
    