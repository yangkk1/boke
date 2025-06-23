# boke
一、项目概述
本项目是一个商城网站，包含用户登录、商城主页、用户个人页面等多个功能页面。项目采用 Django 框架，前端使用 Tailwind CSS 进行样式设计，同时结合 Font Awesome 图标库增强页面视觉效果。本项目是一个商城网站，包含用户登录、商城主页、用户个人页面等多个功能页面。项目采用 Django 框架，前端使用 Tailwind CSS 进行样式设计，同时结合 Font Awesome 图标库增强页面视觉效果。本项目是一个商城网站，包含用户登录、商城主页、用户个人页面等多个功能页面。项目采用 Django 框架，前端使用 Tailwind CSS 进行样式设计，同时结合 Font Awesome 图标库增强页面视觉效果。
二、文件结构与功能模块
1. 模板文件（templates 文件夹）

home.html：商城主页模板，包含轮播图、商品分类、促销活动区和页脚等部分。
轮播图：展示不同的促销信息和新品推荐，吸引用户关注。
商品分类：以图标和文字形式展示多种商品分类，方便用户快速定位所需商品。商品分类：以图标和文字形式展示多种商品分类，方便用户快速定位所需商品。商品分类：以图标和文字形式展示多种商品分类，方便用户快速定位所需商品。
促销活动区：展示限时秒杀、品牌闪购、新品首发等活动，刺激用户购买欲望。
页脚：包含关于我们、帮助中心、客服热线和社交链接等信息，增强用户对商城的了解和信任。


login.html：用户登录页面模板，提供用户登录功能，支持消息提示和第三方登录。
表单头部：显示欢迎信息和登录提示。
消息提示：根据登录结果显示成功或失败消息。
第三方登录：提供微信、微博、QQ 等第三方登录方式。第三方登录：提供微信、微博、QQ 等第三方登录方式。第三方登录：提供微信、微博、QQ 等第三方登录方式。


user_profile.html：用户个人页面模板，包含用户信息展示和退出登录按钮，页脚与主页相似。
用户信息展示：展示用户的基本信息和相关操作。
退出登录：提供退出登录功能，方便用户安全退出。退出登录：提供退出登录功能，方便用户安全退出。退出登录：提供退出登录功能，方便用户安全退出。



2. 模型文件（my_app/models.py）
包含商品库存管理的业务逻辑，提供减少库存的功能，并带有异常处理和日志记录。包含商品库存管理的业务逻辑，提供减少库存的功能，并带有异常处理和日志记录。包含商品库存管理的业务逻辑，提供减少库存的功能，并带有异常处理和日志记录。

异常处理：处理减少库存数量无效和库存不足的情况，确保数据的准确性和业务的正常运行。
日志记录：记录库存变更的详细信息，方便后续的审计和排查问题。
原子操作：使用 Django 的事务原子操作，避免竞态条件，保证数据的一致性。
缓存更新：更新商品库存的缓存，提高系统的性能和响应速度。

3. 配置文件3. 配置文件 3. 配置文件

storpp/wsgi.py：WSGI 配置文件，用于部署 Django 项目。

4. 其他文件4. 其他文件 4. 其他文件

.idea 文件夹：包含项目的配置信息和数据源相关设置。

三、前端设计
1. 样式设计

Tailwind CSS：通过 CDN 引入 Tailwind CSS，并在模板文件中使用其类名进行样式设计，实现响应式布局和美观的界面效果。Tailwind CSS：通过 CDN 引入 Tailwind CSS，并在模板文件中使用其类名进行样式设计，实现响应式布局和美观的界面效果。Tailwind CSS：通过 CDN 引入 Tailwind CSS，并在模板文件中使用其类名进行样式设计，实现响应式布局和美观的界面效果。
自定义颜色和字体：在 Tailwind 配置中定义了主要颜色、次要颜色和中性颜色，同时指定了字体家族，确保页面风格统一。
阴影和动画效果：使用自定义的阴影和动画效果，如卡片悬停阴影和元素滑动动画，提升用户体验。

2. 图标使用

Font Awesome：引入 Font Awesome 图标库，在商品分类、社交链接等部分使用图标，增强页面的视觉吸引力。

四、业务逻辑设计
1. 库存管理
在商品模型中实现减少库存的方法，通过异常处理和日志记录确保库存操作的安全性和可追溯性。
def decrease_stock(self, quantity):
    if quantity <= 0:
        logger.warning(f"尝试减少商品ID#{self.id}的库存，但数量无效: {quantity}")
        raise ValueError("减少的库存数量必须大于0")

    if self.stock < quantity:
        logger.warning(f"商品ID#{self.id}库存不足，当前库存: {self.stock}, 尝试减少: {quantity}")
        raise InventoryException("库存不足")

    try:
        with models.transaction.atomic():
            Product.objects.filter(id=self.id).update(stock=models.F('stock') - quantity)
            self.refresh_from_db()
            StockHistory.objects.create(
                product=self,
                quantity_before=self.stock + quantity,
                quantity_after=self.stock,
                change_reason="订单扣减"
            )
            logger.info(f"成功减少商品ID#{self.id}的库存，减少数量: {quantity}, 剩余库存: {self.stock}")
            cache_key = f'product_stock:{self.id}'
            cache.set(cache_key, self.stock)
    except Exception as e:
        logger.error(f"减少商品ID#{self.id}库存时出错: {str(e)}", exc_info=True)
        raise

3. 用户登录
在登录页面提供用户登录功能，支持消息提示和第三方登录，方便用户快速登录。
五、总结
本商城网站通过合理的文件结构和功能模块设计，实现了用户登录、商品展示、库存管理等核心功能。前端使用 Tailwind CSS 和 Font Awesome 图标库，提供了美观、响应式的界面；后端使用 Django 框架，确保了业务逻辑的安全性和可维护性。同时，通过异常处理和日志记录，提高了系统的稳定性和可追溯性。编辑分享
