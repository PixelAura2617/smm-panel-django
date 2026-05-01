"""
URL configuration for smm_panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as  auth_views
from django.urls import path



urlpatterns = [
    path('', views.dashboard, name='home'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('order/<int:service_id>/', views.order_service, name='order_service'),
    path('add-balance/', views.add_balance, name='add_balance'),
    path('pay/', views.create_payment, name='create_pay'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('order-success/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='orders'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register/', views.register, name='register'),
    path('import-services/',views.import_services, name='import_services'),
    path('wallet/', views.wallet, name='wallet'),
    path('order-status/<int:order_id>/', views.get_order_status, name='order_status'),
    path('withdraw/',views.withdraw, name='withdraw'),
    path('withdraw-history/',views.withdraw_history, name='withdraw_history'),
    path('forgot-password/', auth_views.PasswordResetView.as_view(
    template_name='registration/forgot_password.html',
    email_template_name='registration/password_reset_email.html',
    extra_email_context={'domain': '127.0.0.1:8000'}
), name='password_reset'),

    path('forgot-password/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path("test-mail/", views.test_mail),
    
]