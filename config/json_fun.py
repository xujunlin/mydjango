#!/usr/bin/env python
# encoding: utf-8

from django.http import JsonResponse
from config.res_code import Code


def to_json_data(errno=Code.OK, errmsg="", data=None, **kwargs):
    json_dict = {'errno': errno, 'errmsg': errmsg, 'data': data}
    if kwargs and isinstance(kwargs, dict) and kwargs.keys():
        json_dict.update(kwargs)
    return  JsonResponse(json_dict)

