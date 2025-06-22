# my_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import transaction
import json
from .models import User, Product, Order, OrderItem
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm


# 注册视图
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, '注册成功，请登录。')
            return redirect('login')
        else:
            messages.error(request, '注册失败，请检查输入。')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


# 登录视图
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # 处理“记住我”功能
            if not request.POST.get('remember_me', None):
                request.session.set_expiry(0)
            messages.success(request, '登录成功。')
            return redirect('home')
        else:
            messages.error(request, '用户名或密码错误。')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


# 登出视图
def logout_view(request):
    logout(request)
    messages.success(request, '已成功登出。')
    return redirect('login')


# 主页视图 - 展示商品列表
@login_required
def home_view(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'home.html', {'products': products})


# 商品详情视图
@login_required
def product_detail_view(request, product_id):
    product = Product.objects.get(id=product_id, is_active=True)
    return render(request, 'product_detail.html', {'product': product})


# 搜索视图
@login_required
def search_view(request):
    query = request.GET.get('query', '')
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True
    )
    return render(request, 'search_results.html', {'products': products, 'query': query})


# 购物车视图
@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            total_price += item_total
        except Product.DoesNotExist:
            # 如果商品不存在，从购物车中移除
            del cart[product_id]

    request.session['cart'] = cart
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})


# 添加到购物车
@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})

        if product_id in cart:
            cart[product_id] += quantity
        else:
            cart[product_id] = quantity

        request.session['cart'] = cart
        messages.success(request, '已添加到购物车。')
        return redirect('product_detail', product_id=product_id)


# 更新购物车
@login_required
def update_cart(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        action = request.POST.get('action')
        product_id = request.POST.get('product_id')

        if action == 'update':
            quantity = int(request.POST.get('quantity', 1))
            if product_id in cart:
                if quantity > 0:
                    cart[product_id] = quantity
                else:
                    del cart[product_id]
        elif action == 'remove':
            if product_id in cart:
                del cart[product_id]

        request.session['cart'] = cart
        return redirect('cart')


# 结账视图
@login_required
def checkout_view(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, '购物车为空，无法结账。')
        return redirect('cart')

    cart_items = []
    total_price = 0

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            total_price += item_total
        except Product.DoesNotExist:
            # 如果商品不存在，从购物车中移除
            del cart[product_id]

    request.session['cart'] = cart

    if request.method == 'POST':
        # 创建订单
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                status='pending',
                total_amount=total_price
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['product'].price
                )

        # 清空购物车
        request.session['cart'] = {}
        messages.success(request, '订单创建成功！')
        return redirect('order_confirmation', order_id=order.id)

    return render(request, 'checkout.html', {'cart_items': cart_items, 'total_price': total_price})


# 订单确认视图
@login_required
def order_confirmation_view(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


# 用户订单列表视图
@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})


# 用户个人信息视图
@login_required
def profile_view(request):
    if request.method == 'POST':
        # 处理个人信息更新
        request.user.username = request.POST.get('username')
        request.user.email = request.POST.get('email')
        request.user.save()
        messages.success(request, '个人信息已更新。')
        return redirect('profile')

    return render(request, 'profile.html', {'user': request.user})