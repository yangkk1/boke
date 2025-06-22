# my_app/urls.py
from django.urls import path
from .views import (
    register_view, login_view, logout_view, home_view,
    product_detail_view, search_view, cart_view,
    add_to_cart, update_cart, checkout_view,
    order_confirmation_view, order_history_view,
    profile_view, user_profile_view,
    cart_count
)

urlpatterns = [
    path('cart/count/', cart_count, name='cart_count'),
    path('user_profile/', user_profile_view, name='user_profile'),
    # 用户认证相关URL
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # 主页和商品相关URL
    path('', home_view, name='home'),
    path('product/<int:product_id>/', product_detail_view, name='product_detail'),
    path('search/', search_view, name='search'),
    # 购物车相关URL
    path('cart/', cart_view, name='cart'),
    path('add_to_cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('update_cart/', update_cart, name='update_cart'),
    # 订单相关URL
    path('checkout/', checkout_view, name='checkout'),
    path('order_confirmation/<int:order_id>/', order_confirmation_view, name='order_confirmation'),
    path('order_history/', order_history_view, name='order_history'),
    # 用户个人信息URL
    path('profile/', profile_view, name='profile'),
]