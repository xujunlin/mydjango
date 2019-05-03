#!/usr/bin/env python
# encoding: utf-8
from django import forms
from django.core.validators import RegexValidator

from users.models import Users
from django_redis import get_redis_connection

# 创建手机号的正则校验器
mobile_validator = RegexValidator(r"^1[3-9]\d{9}$", "手机号码格式不正确")

class CheckImgCodeForm(forms.Form):
    """

    """
    mobile = forms.CharField(max_length=11, min_length=11, validators=[mobile_validator,],
                             error_messages={"min_length": '手机长度有误',
                                             "max_length": '手机长度有误',
                                             "required": '手机号不能为空'},)
    text = forms.CharField(max_length=4, min_length=4,
                           error_messages={"min_length": '验证码长度有误',
                                           "max_length": '验证码长度有误',
                                           "required": '验证码不能为空'})
    image_code_id = forms.UUIDField(error_messages={"required": "图片UUID不能为空"})

    def clean(self):
        clean_data = super().clean()
        mobile_num = clean_data.get('mobile')
        image_text = clean_data.get('text')
        img_uuid = clean_data.get('image_code_id')

        # 验证手机
        if Users.objects.filter(mobile=mobile_num):
            raise forms.ValidationError('手机号已经注册，请登录')

        # 验证验证码
        con_redis = get_redis_connection(alias="verify_codes") # 连接数据库
        img_key = 'img_{}'.format(img_uuid)
        real_image_code_origin = con_redis.get(img_key)
        # if real_image_code_origin:
        #     real_image_code = real_image_code_origin.decode('utf8')
        # else:
        #     real_image_code = None
        real_image_code = real_image_code_origin.decode('utf8') if real_image_code_origin else None

        if not real_image_code or image_text != real_image_code:
            raise forms.ValidationError('验证码有误')

        # 检查是否在60s内有发送记录
        sms_flag_fmt = "sms_flag_{}".format(mobile_num).encode('utf-8')
        sms_flag = con_redis.get(sms_flag_fmt)
        if sms_flag:
            raise forms.ValidationError("获取手机短信验证码过于频繁")