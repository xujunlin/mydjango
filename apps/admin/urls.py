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
from admin import views


app_name = 'admin'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', views.IndexView.as_view(), name='index'),
    path('tags/', views.TagManageView.as_view(), name='tags'),
    path('tags/<int:tag_id>/', views.TagEditView.as_view(), name='tag_edit'),
    path('hotnews/', views.HotNewsManageView.as_view(), name='hot_news'),
    path('hotnews/<int:hotnews_id>/', views.HotNewsEditView.as_view(), name='hotnews_edit'),
    path('hotnews/add/', views.HotNewsAddView.as_view(), name='hotnews_add'),
    path('tags/<int:tag_id>/news/', views.NewsByTagIdView.as_view(), name='news_by_tagid'),
    path('news/', views.NewsManageView.as_view(), name='news_manage'),
    path('news/pub/', views.NewsPubView.as_view(), name='news_pub'),
    path('news/images/', views.NewsUploadImage.as_view(), name='upload_image'),
    path('banners/', views.BannerManageView.as_view(), name='banners_manage'),
    path('banners/<int:banner_id>/', views.BannerEditView.as_view(), name='banners_edit'),
    path('banners/add/', views.BannerAddView.as_view(), name='banners_add'),
    path('doc/', views.DocsManageView.as_view(), name="docs_manage"),
    path('doc/<int:banner_id>/', views.DocsEditView.as_view(), name="docs_delete"),

]
