# my_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.db import transaction
import json
from .models import User, Product, Order, OrderItem
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm


@login_required
def cart_count(request):
    try:
        order = Order.objects.get(user=request.user, status='pending')
        count = order.items.count()
        return JsonResponse({'count': count})
    except Order.DoesNotExist:
        return JsonResponse({'count': 0})


@csrf_exempt  # 使用 CSRF 保护，或通过 CSRF 中间件验证
@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            name = data.get('name')
            price = data.get('price')
            quantity = data.get('quantity', 1)

            # 验证商品是否存在
            try:
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'message': '商品不存在'})

            # 获取或创建用户的未完成订单
            order, created = Order.objects.get_or_create(
                user=request.user,
                status='pending',  # 假设 'pending' 表示未完成订单
                defaults={'total_price': 0}
            )

            # 检查商品是否已在订单中
            try:
                order_item = OrderItem.objects.get(order=order, product=product)
                order_item.quantity += quantity
                order_item.price_at_purchase = price  # 更新价格（如果有变化）
                order_item.save()
            except OrderItem.DoesNotExist:
                # 创建新的订单项
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    name=name,  # 保存商品名称（冗余存储，避免后续商品信息变更影响历史订单）
                    price_at_purchase=price,
                    quantity=quantity
                )

            # 更新订单总价
            order.total_price = sum(item.subtotal for item in order.items.all())
            order.save()

            # 返回成功响应
            return JsonResponse({
                'success': True,
                'message': f'{product.name} 已添加到购物车',
                'cart_count': order.items.count()  # 返回购物车商品数量
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '方法不允许'})


# 用户个人信息视图
@login_required
def profile_view(request):
    if request.method == 'POST':
        if 'profile_update' in request.POST:
            # 处理个人信息更新
            request.user.username = request.POST.get('username')
            request.user.email = request.POST.get('email')
            if request.FILES.get('avatar'):
                request.user.avatar = request.FILES.get('avatar')
            request.user.save()
            messages.success(request, '个人信息已更新。')
        elif 'password_update' in request.POST:
            # 处理密码更新
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # 更新会话中的用户认证信息
                messages.success(request, '密码已更新。')
            else:
                for error in form.errors.values():
                    messages.error(request, error)

        return redirect('profile')

    password_form = PasswordChangeForm(request.user)
    return render(request, 'profile.html', {'user': request.user, 'password_form': password_form})



#购物车页面
@login_required
def cart_view(request):
    try:
        order = Order.objects.get(user=request.user, status='pending')
        cart_items = order.items.all()
        total_price = 0

        # 计算每个商品项的小计并更新 total_price
        for item in cart_items:
            item.subtotal = item.quantity * item.price_at_purchase
            total_price += item.subtotal

    except Order.DoesNotExist:
        cart_items = []
        total_price = 0

    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})
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
                try:
                    product = Product.objects.get(id=product_id, is_active=True)
                    if quantity > product.stock:
                        quantity = product.stock
                        messages.warning(request, f"商品 {product.name} 库存不足，已调整数量。")
                    if quantity > 0:
                        cart[product_id] = quantity
                    else:
                        del cart[product_id]
                        messages.success(request, "商品已从购物车中移除。")
                except Product.DoesNotExist:
                    del cart[product_id]
                    messages.error(request, "商品不存在，已从购物车中移除。")
        elif action == 'remove':
            if product_id in cart:
                del cart[product_id]
                messages.success(request, "商品已从购物车中移除。")

        request.session['cart'] = cart
        return redirect('cart')

#用户页面视图
@login_required
def user_profile_view(request):
    return render(request, 'user_profile.html', {'user': request.user})

# 注册视图
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # 手动保存额外字段
            user.phone = form.cleaned_data.get('phone')
            user.address = form.cleaned_data.get('address')
            user.avatar = form.cleaned_data.get('avatar')
            user.save()
            messages.success(request, '注册成功，请登录。')
            return redirect('login')
        else:
            messages.error(request, '注册失败，请检查输入。')
    else:
        form = CustomUserCreationForm()
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