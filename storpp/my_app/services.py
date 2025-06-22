# my_app/services.py
from .models import Order, OrderItem, Product, InventoryException
from django.db import transaction

def process_batch_order(user_id, items_data):
    failed_items = []
    with transaction.atomic():
        try:
            order = Order.objects.create(user_id=user_id)
            for item_data in items_data:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity')
                try:
                    product = Product.get_by_id(product_id)
                    product.decrease_stock(quantity)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price_at_purchase=product.price
                    )
                except (Product.DoesNotExist, InventoryException) as e:
                    failed_items.append({
                        'product_id': product_id,
                        'quantity': quantity,
                        'error': str(e)
                    })
            order.calculate_total_amount()
            return order, failed_items
        except Exception as e:
            # 出现异常时回滚事务
            transaction.set_rollback(True)
            return None, [{'error': str(e)}]