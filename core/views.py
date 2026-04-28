from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.timezone import now
from datetime import timedelta
from django.db.models.functions import TruncDate

from .models import Service, Order, Profile, Transaction, WithdrawRequest

import razorpay
import requests


# 🔐 CONFIG
API_URL = "https://myapp.smmsurge.com/api/v2"
API_KEY = settings.SMM_API_KEY


# 🔹 HOME
def index(request):
    return render(request, 'index.html')


# 🔄 UPDATE ORDER STATUS
def update_order_status(order):
    if not order.provider_order_id:
        return

    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'status',
            'order': order.provider_order_id
        }, timeout=10)

        data = response.json()

        if "status" in data:
            order.status = data["status"].lower()
            order.save()

    except Exception as e:
        print("STATUS ERROR:", e)


# 🔹 DASHBOARD
@login_required
def dashboard(request):
    query = request.GET.get('q')
    category = request.GET.get('category')

    services = Service.objects.all()

    if query:
        services = services.filter(name__icontains=query)

    if category:
        services = services.filter(category=category)

    categories = Service.objects.values_list('category', flat=True).distinct()

    orders = Order.objects.filter(user=request.user)

    for o in orders[:5]:
        update_order_status(o)

    profile, _ = Profile.objects.get_or_create(user=request.user)

    total_profit = orders.aggregate(total=Sum('profit'))['total'] or 0
    total_orders = orders.count()

    total_spent = orders.aggregate(total=Sum('price'))['total'] or 0
    total_deposit = Transaction.objects.filter(user=request.user, status='success').aggregate(total=Sum('amount'))['total'] or 0

    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'dashboard.html', {
        'services': services,
        'orders': orders,
        'balance': profile.balance,
        'total_orders': total_orders,
        'transactions': transactions,
        'categories': categories,
        'total_spent': total_spent,
        'total_deposit': total_deposit,
    })


# 🔹 ORDER SERVICE (🔥 FIXED)
@login_required
def order_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        link = request.POST.get('link')
        quantity = request.POST.get('quantity')

        # 🔹 VALIDATION
        if not link or not quantity or not quantity.isdigit():
            return render(request, 'order.html', {
                'service': service,
                'error': 'Invalid input ❌'
            })

        quantity = int(quantity)

        if quantity <= 0:
            return render(request, 'order.html', {
                'service': service,
                'error': 'Quantity must be greater than 0 ❌'
            })

        # 🔹 PROFILE
        profile, _ = Profile.objects.get_or_create(user=request.user)

        # 🔥 MIN MAX CHECK
        if quantity < service.min_qty or quantity > service.max_qty:
            return render(request, 'order.html', {
                'service': service,
                'error': f"Min {service.min_qty} - Max {service.max_qty}"
            })

        # 🔥 PRICING LOGIC (RESSELLER SUPPORT)
        base_price = service.cost_price

        selling_price = base_price + (base_price * service.margin_percent / 100)

        if profile.is_reseller:
            selling_price += (base_price * profile.reseller_margin / 100)

        total_price = (selling_price / 1000) * quantity
        total_cost = (base_price / 1000) * quantity

        profit = total_price - total_cost

        # 🔹 BALANCE CHECK
        if profile.balance < total_price:
            return render(request, 'order.html', {
                'service': service,
                'error': 'Insufficient balance ❌'
            })

        # 🔥 API CALL
        try:
            response = requests.post(API_URL, data={
                'key': API_KEY,
                'action': 'add',
                'service': service.provider_service_id,
                'link': link,
                'quantity': quantity
            }, timeout=15)

            data = response.json()

        except Exception as e:
            print("API ERROR:", e)
            return render(request, 'order.html', {
                'service': service,
                'error': 'API connection failed ❌'
            })

        if "order" not in data:
            return render(request, 'order.html', {
                'service': service,
                'error': f"API Error ❌ {data}"
            })

        # 💸 BALANCE CUT
        profile.balance -= total_price
        profile.save()

        # 📦 SAVE ORDER
        Order.objects.create(
            user=request.user,
            service=service,
            link=link,
            quantity=quantity,
            price=total_price,
            profit=profit,
            status='pending',
            provider_order_id=data.get('order')
        )

        # 🎁 REFERRAL BONUS
        if profile.referred_by:
            ref_profile = Profile.objects.get(user=profile.referred_by)
            bonus = round(profit * 0.1, 2)

            ref_profile.balance += bonus
            ref_profile.save()

            Transaction.objects.create(
                user=profile.referred_by,
                amount=bonus,
                status='referral'
            )

        messages.success(request, 'Order placed successfully! 🎉')
        return redirect('order_history')

    return render(request, 'order.html', {'service': service})

# 🔹 ADD BALANCE
@login_required
def add_balance(request):
    return render(request, 'add_balance.html')


# 🔹 CREATE PAYMENT
@login_required
def create_payment(request):
    if request.method == 'POST':
        amount = int(request.POST.get('amount', 0))

        if amount <= 0:
            return render(request, 'add_balance.html', {
                'error': 'Invalid amount ❌'
            })

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        payment = client.order.create({
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": "1"
        })

        return render(request, "payment.html", {
            "payment": payment,
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID
        })

    return redirect('add_balance')


# 🔹 PAYMENT SUCCESS
@login_required
def payment_success(request):
    if request.method == "POST":
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        params_dict = {
            'razorpay_order_id': request.POST.get('razorpay_order_id'),
            'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
            'razorpay_signature': request.POST.get('razorpay_signature')
        }

        amount = int(request.POST.get('amount', 0))

        try:
            client.utility.verify_payment_signature(params_dict)

            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.balance += amount
            profile.save()

            Transaction.objects.create(
                user=request.user,
                amount=amount,
                status='success'
            )

            return render(request, 'add_balance_success.html', {
                'amount': amount
            })

        except:
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                status='failed'
            )

            return render(request, 'add_balance.html', {
                'error': 'Payment verification failed ❌'
            })

    return redirect('add_balance')


# 🔹 ORDER HISTORY
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    for o in orders[:10]:
        update_order_status(o)

    return render(request, 'order_history.html', {'orders': orders})


# 🔹 ADMIN DASHBOARD
@staff_member_required
def admin_dashboard(request):
    orders = Order.objects.all()

    # 🔹 BASIC STATS
    total_orders = orders.count()
    total_users = User.objects.count()

    total_revenue = sum(o.price for o in orders)
    total_cost = sum((o.price - o.profit) for o in orders)
    total_profit = sum(o.profit for o in orders)

    # 🔹 TODAY PROFIT
    today = now().date()
    today_profit = orders.filter(created_at__date=today).aggregate(
        total=Sum('profit')
    )['total'] or 0

    # 🔹 LAST 7 DAYS PROFIT
    last_7_days = now() - timedelta(days=7)
    week_profit = orders.filter(created_at__gte=last_7_days).aggregate(
        total=Sum('profit')
    )['total'] or 0

    # 🔥 GRAPH DATA (LAST 7 DAYS)
    daily_data = (
        orders
        .filter(created_at__gte=last_7_days)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('profit'))
        .order_by('date')
    )

    dates = [str(i['date']) for i in daily_data]
    profits = [float(i['total'] or 0) for i in daily_data]

    return render(request, 'admin_dashboard.html', {
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'today_profit': today_profit,
        'week_profit': week_profit,

        # 🔥 graph data
        'dates': dates,
        'profits': profits,
    })

# 🔹 REGISTER
def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")
        referral_code = request.POST.get("referral_code")

        if password != confirm:
            return render(request, "registration/register.html", {"error": "Passwords do not match ❌"})

        if User.objects.filter(username=username).exists():
            return render(request, "registration/register.html", {"error": "Username exists ❌"})

        user = User.objects.create_user(username=username, password=password)

        if referral_code:
            try:
                ref_profile = Profile.objects.get(referral_code=referral_code)
                profile = Profile.objects.get(user=user)
                profile.referred_by = ref_profile.user
                profile.save()
            except:
                pass

        return redirect("login")

    return render(request, "registration/register.html")


# 🔹 IMPORT SERVICES (🔥 FIXED)
@staff_member_required
def import_services(request):
    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'services'
        }, timeout=20)

        data = response.json()

        count = 0

        for s in data:
            Service.objects.update_or_create(
                provider_service_id=s['service'],
                defaults={
                    'name': s['name'],
                    'category': s.get('category', 'Other'),
                    'cost_price': float(s['rate']),
                    'margin_percent': 30
                }
            )
            count += 1

        print(f"Imported {count} services")

    except Exception as e:
        print("IMPORT ERROR:", e)

    return redirect('admin_dashboard')
 
@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def wallet(request):
    trasnations = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'wallet.html', {'transations': trasnations})

@login_required
def get_order_status(request, order_id):
     order = get_object_or_404(Order, id=order_id, user=request.user)

     update_order_status(order)
     return render(JsonResponse({
        'status': order.status
        }))

@login_required
def withdraw(request):
    profile = Profile.objects.get(user=request.user)

    if request.method == "POST":
        amount = float(request.POST.get("amount", 0))
        upi_id = request.POST.get("upi_id")

        # ❌ validation
        if amount <= 0:
            return render(request, "withdraw.html", {"error": "Invalid amount"})

        if amount > profile.balance:
            return render(request, "withdraw.html", {"error": "Insufficient balance"})

        # 💸 deduct balance
        profile.balance -= amount
        profile.save()

        # 🧾 save request
        WithdrawRequest.objects.create(
            user=request.user,
            amount=amount,
            upi_id=upi_id
        )

        return render(request, "withdraw.html", {"success": "Withdraw request submitted ✅"})

    return render(request, "withdraw.html")

@login_required
def withdraw_history(request):
    data = WithdrawRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'withdraw_history.html', {'data': data})