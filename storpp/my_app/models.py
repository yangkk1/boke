# products/models.py

import uuid
import logging
from django.db import models
from django.conf import settings
from django.db.models import F
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

# 获取日志记录器
logger = logging.getLogger('products')


# 自定义异常类
class InventoryException(Exception):
    """库存相关异常"""
    pass


class OrderException(Exception):
    """订单相关异常"""
    pass


class ProductNotFoundException(Exception):
    """商品未找到异常"""
    pass


# 用户模型 - 扩展Django内置用户模型
class User(AbstractUser):
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name="手机号")
    address = models.TextField(blank=True, null=True, verbose_name="地址")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="头像")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.username

    def get_full_name_or_username(self):
        """获取用户全名或用户名"""
        if self.get_full_name():
            return self.get_full_name()
        return self.username

    def place_order(self, items_data):
        """用户下单的快捷方法"""
        from .services import process_batch_order  # 避免循环导入
        order, failed_items = process_batch_order(self.id, items_data)
        return order, failed_items


# 商品分类模型
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名称")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='children',
                               verbose_name="父分类")
    description = models.TextField(blank=True, verbose_name="分类描述")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "商品分类"
        verbose_name_plural = "商品分类"


# 商品模型
class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="商品名称")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True, related_name='products',
                                 verbose_name="分类")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="价格")
    stock = models.IntegerField(default=0, verbose_name="库存")
    description = models.TextField(blank=True, verbose_name="商品描述")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="商品图片")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.name

    def decrease_stock(self, quantity):
        """减少库存，带异常处理和日志记录"""
        if quantity <= 0:
            logger.warning(f"尝试减少商品ID#{self.id}的库存，但数量无效: {quantity}")
            raise ValueError("减少的库存数量必须大于0")

        if self.stock < quantity:
            logger.warning(f"商品ID#{self.id}库存不足，当前库存: {self.stock}, 尝试减少: {quantity}")
            raise InventoryException("库存不足")

        try:
            with models.transaction.atomic():
                # 使用F表达式避免竞态条件
                Product.objects.filter(id=self.id).update(stock=F('stock') - quantity)
                # 刷新当前实例
                self.refresh_from_db()
                # 记录库存变更历史
                StockHistory.objects.create(
                    product=self,
                    quantity_before=self.stock + quantity,
                    quantity_after=self.stock,
                    change_reason="订单扣减"
                )
                logger.info(f"成功减少商品ID#{self.id}的库存，减少数量: {quantity}, 剩余库存: {self.stock}")
        except Exception as e:
            logger.error(f"减少商品ID#{self.id}库存时出错: {str(e)}", exc_info=True)
            raise

    def increase_stock(self, quantity):
        """增加库存，带异常处理和日志记录"""
        if quantity <= 0:
            logger.warning(f"尝试增加商品ID#{self.id}的库存，但数量无效: {quantity}")
            raise ValueError("增加的库存数量必须大于0")

        try:
            with models.transaction.atomic():
                Product.objects.filter(id=self.id).update(stock=F('stock') + quantity)
                self.refresh_from_db()
                # 记录库存变更历史
                StockHistory.objects.create(
                    product=self,
                    quantity_before=self.stock,
                    quantity_after=self.stock + quantity,
                    change_reason="库存补充"
                )
                logger.info(f"成功增加商品ID#{self.id}的库存，增加数量: {quantity}, 现有库存: {self.stock}")
        except Exception as e:
            logger.error(f"增加商品ID#{self.id}库存时出错: {str(e)}", exc_info=True)
            raise

    @classmethod
    def get_by_id(cls, product_id):
        """通过ID获取商品，使用自定义异常"""
        try:
            return cls.objects.get(id=product_id)
        except cls.DoesNotExist:
            logger.warning(f"尝试获取不存在的商品，ID: {product_id}")
            raise ProductNotFoundException(f"商品ID#{product_id}不存在")

    @classmethod
    def create_product(cls, name, price, stock=0, description="", category=None, image=None):
        """创建商品的类方法，带异常处理"""
        try:
            product = cls.objects.create(
                name=name,
                price=price,
                stock=stock,
                description=description,
                category=category,
                image=image
            )
            logger.info(f"创建新商品，ID: {product.id}, 名称: {name}")
            return product
        except Exception as e:
            logger.error(f"创建商品失败: {str(e)}", exc_info=True)
            raise


# 订单模型
class Order(models.Model):
    ORDER_STATUS = (
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('shipping', '配送中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    )
    order_number = models.CharField(max_length=36, default=uuid.uuid4, editable=False, unique=True,
                                    verbose_name="订单号")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="用户")
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending', verbose_name="订单状态")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="订单总额")
    shipping_address = models.TextField(blank=True, null=True, verbose_name="配送地址")
    payment_method = models.CharField(max_length=50, blank=True, null=True, verbose_name="支付方式")
    payment_time = models.DateTimeField(blank=True, null=True, verbose_name="支付时间")
    shipping_time = models.DateTimeField(blank=True, null=True, verbose_name="发货时间")
    completed_time = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.order_number

    def calculate_total_amount(self):
        """计算订单总额"""
        total = sum(item.quantity * item.price_at_purchase for item in self.items.all())
        self.total_amount = total
        self.save()
        logger.info(f"订单ID#{self.id}总额已更新为: {total}")
        return total

    def cancel_order(self):
        """取消订单，退还库存"""
        if self.status not in ['pending', 'paid', 'shipping']:
            logger.warning(f"尝试取消状态为 {self.status} 的订单ID#{self.id}，只有待支付、已支付或配送中的订单可以取消")
            raise OrderException(f"订单状态不允许取消: {self.status}")

        try:
            with models.transaction.atomic():
                self.status = 'cancelled'
                self.save()
                logger.info(f"订单ID#{self.id}已成功取消")

                # 如果订单已支付，需要退还库存
                if self.status in ['paid', 'shipping']:
                    for item in self.items.all():
                        item.product.increase_stock(item.quantity)
                        logger.info(f"订单取消后，已退还商品ID#{item.product.id}的库存: {item.quantity}")
        except Exception as e:
            logger.error(f"取消订单ID#{self.id}时出错: {str(e)}", exc_info=True)
            raise


# 订单商品项模型
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="订单")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items',
                                verbose_name="商品")
    quantity = models.IntegerField(default=1, verbose_name="数量")
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="购买时价格")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in Order#{self.order.id}"


# 库存历史记录模型
class StockHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_history', verbose_name="商品")
    quantity_before = models.IntegerField(verbose_name="变更前库存")
    quantity_after = models.IntegerField(verbose_name="变更后库存")
    change_reason = models.CharField(max_length=200, verbose_name="变更原因")
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="相关订单")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"商品ID#{self.product.id}库存变更: {self.quantity_before} → {self.quantity_after}"


# 信号处理 - 记录模型操作日志
@receiver(pre_save, sender=Product)
def log_product_pre_save(sender, instance, **kwargs):
    if instance.pk:  # 检查是否是更新操作
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            changes = {}
            for field in instance._meta.get_fields():
                if field.name in ['created_at', 'updated_at']:
                    continue
                try:
                    old_value = getattr(old_instance, field.name)
                    new_value = getattr(instance, field.name)
                    if old_value != new_value:
                        changes[field.name] = (old_value, new_value)
                except Exception:
                    continue

            if changes:
                logger.info(f"商品ID#{instance.pk}即将更新，变更内容: {changes}")
        except sender.DoesNotExist:
            # 可能是在创建对象，忽略
            pass


@receiver(post_save, sender=Product)
def log_product_post_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"新商品已创建，ID: {instance.id}, 名称: {instance.name}")
    else:
        logger.info(f"商品ID#{instance.id}已更新")


@receiver(pre_delete, sender=Product)
def log_product_pre_delete(sender, instance, **kwargs):
    logger.warning(f"即将删除商品ID#{instance.id}, 名称: {instance.name}")


@receiver(post_delete, sender=Product)
def log_product_post_delete(sender, instance, **kwargs):
    logger.warning(f"商品已删除，ID: {instance.id}, 名称: {instance.name}")


@receiver(pre_save, sender=Order)
def log_order_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            logger.info(f"订单ID#{instance.pk}状态变更: {old_instance.status} → {instance.status}")


@receiver(post_save, sender=Order)
def log_order_post_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"新订单已创建，ID: {instance.id}, 用户: {instance.user.username}, 订单号: {instance.order_number}")
    else:
        if instance.status == 'paid':
            logger.info(f"订单ID#{instance.id}已支付，开始处理库存扣减")


@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, created, **kwargs):
    if created:
        logger.info(f"订单ID#{instance.order.id}添加新商品项: {instance.product.name} x {instance.quantity}")
        instance.order.calculate_total_amount()