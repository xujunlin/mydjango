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
from django.urls import path, include
from news import views


app_name = 'news'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', views.IndexView.as_view(), name='index'),
    path('news/', views.NewListView.as_view(), name='news_list'),
    path('news/banners/', views.NewsBanner.as_view(), name='news_banners'),
    path('news/<int:news_id>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('news/<int:news_id>/comments/', views.NewsCommentView.as_view(), name='news_comment'),
]
