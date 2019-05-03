from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from django_redis import get_redis_connection

from config.captcha.captcha import captcha
from config.yuntongxun.sms import CCP
from users import models
from verifications.forms import CheckImgCodeForm
from verifications import constants
from config.json_fun import to_json_data
from config.res_code import Code, error_map

import random
import string
import logging
import json

# Create your views here.

# 导入日志器
logger = logging.getLogger('django')

class ImageCode(View):
    """
    /image codes/
    图片验证码模块
    """
    def get(self, request, image_code_id):
        # 生成验证码并分别接受图片和数据
        text, image = captcha.generate_captcha()
        # 连接数据库
        con_redis = get_redis_connection(alias="verify_codes")
        # 接受ajax生成的UUID
        img_key = 'img_{}'.format(image_code_id)
        # 数据库保存图片数据（UUID，图片保存期，图片内容）
        con_redis.setex(img_key, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        logger.info("image_code: {}".format(text))
        return HttpResponse(content=image, content_type='image/jpg')


class CheckUsernameView(View):
    """
    /username/(?P<username>\w{5,20})/
    用户名验证模块
    """
    def get(self, request, username):
        # 数据库查询用户名是否注册（能否查到）
        count = models.Users.objects.filter(username=username).count()
        # 生成json数据
        data = {
            'count': count,
            'username': username
        }
        return to_json_data(data=data)


class CheckMobileView(View):
    """
    /mobile/(?P<mobile>1[3-9]\d{9})/
    用户手机验证模块
    """
    def get(self, request, mobile):
        # 数据库查询手机是否注册（能否查到）
        count = models.Users.objects.filter(mobile=mobile).count()
        # 生成json数据
        data = {
            'count': count,
            'mobile': mobile
        }
        return to_json_data(data=data)


class SmsCodesView(View):
    """
    /sms_codes/
    短信验证码模块
    """
    # 1.获取参数（前端传输过来）
    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        dict_data = json.loads(json_data.decode("utf8"))

        # 2.验证参数（form验证is_valid()）
        form = CheckImgCodeForm(data=dict_data)
        if form.is_valid():
            # 3.生成验证码并发送
            mobile = form.cleaned_data.get('mobile')
            sms_num = ''.join([random.choice(string.digits) for _ in range(constants.SMS_CODE_NUMS)])
            # 连接数据库
            con_redis = get_redis_connection(alias='verify_codes')
            p1 = con_redis.pipeline()
            sms_text_fmt = 'sms_{}'.format(mobile)
            sms_flg_fmt = 'sms_flag_{}'.format(mobile)
            try:
                p1.setex(sms_flg_fmt, constants.SMS_CODE_REDIS_INTERVAL, constants.SMS_CODE_TD)
                p1.setex(sms_text_fmt, constants.SMS_CODE_REDIS_EXPIRES, sms_num)
                # 让管道通知redis执行命令
                p1.execute()
            except Exception as e:
                logger.debug('redis执行异常'.format(e))
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
            logger.info("Sms code: {}".format(sms_num))

            return to_json_data(errno=Code.OK, errmsg='发送正常')

            # # 4.发送短信验证码
            # try:
            #     result = CCP().send_template_sms(mobile,
            #                                      [sms_num, constants.SMS_CODE_REDIS_EXPIRES, constants.SMS_CODE_TD])
            # except Exception as e:
            #     logger.error('发送验证码短信[错误][mobile: %s, message: %s]'% (mobile, e))
            #     return to_json_data(errno=Code.SMSERROR, errmsg=error_map[Code.SMSERROR])
            #
            # else:
            #     if result == 0:
            #         logger.info('发送短信验证码[成功][mobile: %s, sms_code: %s]'% (mobile, sms_num))
            #         return to_json_data(errno=Code.OK, errmsg='短信验证码发送成功')
            #     else:
            #         logger.warning('发送短信验证码[失败][mobile: %s]'% mobile)
            #         return to_json_data(errno=Code.SMSFAIL, errmsg=error_map[Code.SMSFAIL])
            # 5.返回前端
        else:
            # 定义一个错误列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))

            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


