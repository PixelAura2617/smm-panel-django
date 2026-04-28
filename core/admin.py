from django.contrib import admin
from .models import Service, Order, Profile, Transaction, WithdrawRequest


# 🔹 SERVICE ADMIN
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'cost_price', 'margin_percent', 'provider_service_id')
    search_fields = ('name', 'category')
    list_filter = ('category',)


# 🔹 ORDER ADMIN
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'service', 'quantity', 'price', 'profit', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'service__name')
    ordering = ('-created_at',)


# 🔹 PROFILE ADMIN (🔥 RESSELLER INCLUDED)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'referral_code', 'referred_by', 'is_reseller', 'reseller_margin')
    search_fields = ('user__username', 'referral_code')
    list_filter = ('referred_by', 'is_reseller')


# 🔹 TRANSACTION ADMIN (🔥 FIXED)
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username',)


# 🔹 WITHDRAW ADMIN
@admin.register(WithdrawRequest)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'upi_id', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username',)

    actions = ['approve_withdraw', 'reject_withdraw']

    # ✅ APPROVE
    def approve_withdraw(self, request, queryset):
        queryset.update(status='approved')

    approve_withdraw.short_description = "Approve selected withdraw requests"

    # ❌ REJECT
    def reject_withdraw(self, request, queryset):
        queryset.update(status='rejected')

    reject_withdraw.short_description = "Reject selected withdraw requests"