import logging
from django.core.wsgi import get_wsgi_application
import os

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'storpp.settings')
application = get_wsgi_application()

from my_app.models import User, Category, Product, Order, OrderItem, StockHistory

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('products')

# 创建用户
def create_users():
    users = []
    user_data = [
        {'username': 'user1', 'password': 'password1', 'phone': '12345678901', 'address': '地址1'},
        {'username': 'user2', 'password': 'password2', 'phone': '12345678902', 'address': '地址2'},
        {'username': 'user3', 'password': 'password3', 'phone': '12345678903', 'address': '地址3'}
    ]
    for data in user_data:
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            phone=data['phone'],
            address=data['address']
        )
        users.append(user)
        logger.info(f"创建用户: {user.username}")
    return users

# 创建商品分类
def create_categories():
    categories = []
    category_data = [
        {'name': '电子产品', 'description': '各类电子产品分类'},
        {'name': '服装', 'description': '各种款式的服装分类'},
        {'name': '食品', 'description': '各类食品分类'}
    ]
    for data in category_data:
        category = Category.objects.create(
            name=data['name'],
            description=data['description']
        )
        categories.append(category)
        logger.info(f"创建商品分类: {category.name}")
    return categories

# 创建商品
def create_products(categories):
    products = []
    product_data = [
        {'name': '智能手机', 'price': 5999.00, 'stock': 100, 'description': '高性能智能手机', 'category': categories[0]},
        {'name': 'T恤', 'price': 59.00, 'stock': 200, 'description': '舒适纯棉T恤', 'category': categories[1]},
        {'name': '巧克力', 'price': 29.00, 'stock': 300, 'description': '美味巧克力', 'category': categories[2]}
    ]
    for data in product_data:
        product = Product.create_product(
            name=data['name'],
            price=data['price'],
            stock=data['stock'],
            description=data['description'],
            category=data['category']
        )
        products.append(product)
        logger.info(f"创建商品: {product.name}")
    return products

# 创建订单
def create_orders(users, products):
    orders = []
    import random
    for user in users:
        items_data = []
        for _ in range(random.randint(1, 3)):
            product = random.choice(products)
            quantity = random.randint(1, 10)
            items_data.append({
                'product_id': product.id,
                'quantity': quantity
            })
        order, failed_items = user.place_order(items_data)
        if order:
            orders.append(order)
            logger.info(f"用户 {user.username} 创建订单: {order.order_number}")
            if failed_items:
                logger.warning(f"订单创建失败的商品项: {failed_items}")
    return orders

# 主函数
def main():
    users = create_users()
    categories = create_categories()
    products = create_products(categories)
    orders = create_orders(users, products)

    logger.info("示例数据添加完成")

if __name__ == "__main__":
    main()