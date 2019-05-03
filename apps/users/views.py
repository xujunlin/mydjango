from django.shortcuts import render, redirect, reverse
from django.views import View

from django.contrib.auth import login, logout

from users.forms import RegisterForm, LoginForm
from users.models import Users
from config.json_fun import to_json_data
from config.res_code import Code, error_map
import json


# Create your views here.

class RegisterView(View):
    """
    /register/
    """
    def get(self, request):
        return render(request, 'users/register.html')


    def post(self, request):
        # 1.获取参数
        json_data = request.body  # byte str
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 2.校验参数
        form = RegisterForm(data=dict_data)
        if form.is_valid():
            # 3.存入数据库
            usename = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            mobile = form.cleaned_data.get('mobile')

            user = Users.objects.create_user(username=usename, password=password, mobile=mobile)
            login(request.user)
            return to_json_data(errmsg='恭喜你，注册成功')
        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))

            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LoginView(View):
    """
    /login/
    """
    def get(self, request):
        return render(request, 'users/login.html')

    def post(self, request):
        # 1.获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        # 2.校验参数
        form = LoginForm(data=dict_data, request=request)
        # 3.返回前端
        if form.is_valid():
            return to_json_data(errmsg='恭喜，登录成功')

        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))

            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LogoutView(View):
    """"""
    def get(self, request):
        logout(request)
        return redirect(reverse('users:login'))
