#!/usr/bin/env python
# encoding: utf-8
from django.db import models


class ModelBase(models.Model):
    """
    继承类模型，用于模型的继承，包含：创建时间，修改时间，删除等。
    """
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        # 在数据库迁移中不会生成表。仅仅用于继承
        abstract = True