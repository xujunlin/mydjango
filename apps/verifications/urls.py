#!/usr/bin/env python
# encoding: utf-8
"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.urls import path, re_path, include
from verifications import views

app_name = 'verifications'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('image_code/<uuid:image_code_id>/', views.ImageCode.as_view(), name='image_code'),
    re_path('username/(?P<username>\w{5,20})/', views.CheckUsernameView.as_view(), name='check_username'),
    re_path('mobile/(?P<mobile>1[3-9]\d{9})/', views.CheckMobileView.as_view(), name='check_mobile'),
    path('sms_code/', views.SmsCodesView.as_view(), name='sms_code')
]
