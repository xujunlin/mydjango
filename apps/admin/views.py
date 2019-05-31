import json
import logging
from datetime import datetime
from urllib.parse import urlencode

import qiniu
from config.secrets import qiniu_secret_info
from django.http import JsonResponse

from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count
from django.shortcuts import render
from django.views import View

from users.models import Users
from admin import forms
from doc.models import Doc
from news import models
from course.models import Course, CourseCategory
from course.models import Teacher

from config.json_fun import to_json_data
from config.res_code import Code, error_map
from config import paginator_script
from admin import constants
from mysite import settings
from config.fastdfs.fdfs import FDFS_Client

logger = logging.getLogger('django')
# Create your views here.
# 主页
class IndexView(View):
    """
    /admin/
    后台管理页主页
    """
    def get(self, request):
        """
        :param request: 无
        :return: 前端渲染页
        """
        return render(request, 'admin/index/index.html')


# 标签管理
class TagManageView(View):
    """
    /admin/tags/
    标签管理页
    """
    def get(self, request):
        """
        数据库取全部标签数据并渲染到前端
        :param request: 无
        :return: 前端渲染页
        """
        # 分组查询 value返回字典
        tags = models.Tag.objects.select_related('news').values(
            'id', 'name'
        ).annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news')

        return render(request, 'admin/news/tags_manage.html', locals())

    def post(self, request):
        """
        :param request: 返回json_dict到前端
        :return: JsonResponse(json_dict)
        """
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 修改
        tag_name = dict_data.get('name')
        if tag_name:
            tag_name = tag_name.strip()
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            tag_instance, tag_boolean = tag_tuple
            if tag_boolean:
                news_tag_dict = {
                    'id': tag_instance.id,
                    'name': tag_instance.name
                }
                return to_json_data(errmsg='标签创建成功', data=news_tag_dict)
            else:
                return to_json_data(errno=Code.DATAEXIST, errmsg='标签已存在')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不能为空')


# 标签编辑
class TagEditView(View):
    """
    /admin/tag/<int:tag_id>
    """
    def delete(self, request, tag_id):
        """
        :param request:
        :param tag_id: 前端传入和数据库对比验证
        :return: JsonResponse(json_dict)
        """
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            tag.is_delete = True
            tag.save(update_fields = ['is_delete'])
            return to_json_data(errmsg='标签删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不存在')

    def put(self, request, tag_id):
        """
        :param request: request.body
        :param tag_id:
        :return: 前端传入和数据库对比验证
        """
        json_data = request.body
        # 校验前端传入是否正确
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name').strip()

        # 比对数据库
        tag = models.Tag.objects.only('name').filter(id=tag_id).first()
        if tag:
            if not models.Tag.objects.only('id').filter(name=tag_name).exists():
                if tag.name == tag_name:
                    return to_json_data(errno=Code.PARAMERR, errmsg='标签未修改')
                tag.name = tag_name
                tag.save(update_fields=['name'])
                return to_json_data(errmsg='标签更新成功')
            else:
                return to_json_data(errmsg='标签名已存在')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不存在')


# 热门新闻管理
class HotNewsManageView(View):
    """
    /admin/hotnews/
    """
    def get(self, request):
        """
        :param request:
        :return: 前端渲染页面
        """
        hot_news = models.HotNews.objects.select_related('news__tag').only(
            'news__title', 'news__tag__name', 'priority', 'news_id'
        ).filter(is_delete=False).order_by('priority', '-news__clicks')[:constants.SHOW_HOTNEWS_COUNT]
        return render(request, 'admin/news/news_hot.html', locals())


# 热门新闻编辑
class HotNewsEditView(View):
    """
    /admin/hotnews/<int:tag_id>/
    """
    def delete(self, request, hotnews_id):
        """
        :param request:
        :param hotnews_id:
        :return: 前端传入和数据库对比验证
        """
        # 获取参数并验证
        tag = models.Tag.objects.only('id').filter(id=hotnews_id).first()
        if tag:
            tag.is_delete = True
            # 更新参数
            tag.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='标签删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不存在')

    def put(self, request, hotnews_id):
        json_data = request.body
        # 验证参数
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误')

        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if not hotnews:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的热门文章不存在')
        if hotnews.priority == priority:
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级优先级无变化')
        hotnews.priority = priority
        hotnews.save(update_fields=['priority', 'update_time'])
        return to_json_data(errmsg='热门文章更新成功')


# 热门新闻新增
class HotNewsAddView(View):
    """
    /admin/hotnews/add/
    """
    def get(self, request):
        """
        :param request:
        :return:
        """
        tags = models.Tag.objects.select_related('news').values(
            'id', 'name'
        ).annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news')

        priority_dict = dict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        """
        :param request:
        :return:
        """
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('热门文章：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误')
        except Exception as e:
            logger.info('热门文章：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hotnews, is_created = hotnews_tuple
        hotnews.priority = priority
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg='热门新闻修改成功')


# 新闻搜索
class NewsByTagIdView(View):
    """
    /admin/tags/<int:tag_id>/news/
    """
    def get(self, request, tag_id):
        news = models.News.objects.filter(is_delete=False, tag_id=tag_id).values('id', 'title')
        news_list = [i for i in news]
        return to_json_data(data={
            'news': news_list
        })


# 新闻管理
class NewsManageView(View):
    """
    请求方式：get
    携带参数：start_time, end_time title, author_name, tag_id
    返回参数：title, author_username, tag_name, update_time, id
    /admin/news/
    """
    def get(self, request):
        """
        :param request: 验证参数
        :return: 前端渲染页面
        """
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        newses = models.News.objects.select_related('author', 'tag').only(
            'title', 'author__username', 'tag__name', 'update_time'
        ).filter(is_delete=False)
        # 通过标签id进行过滤
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info("标签错误：\n{}".format(e))
            tag_id = 0

        if tag_id:
            newses = newses.filter(tag_id=tag_id)

        # 通过时间进行过滤
        try:
            # 查询到的起始时间
            start_time = request.GET.get('start_time', '')
            # 对时间格式化
            start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''
            # 查询截止的时间
            end_time = request.GET.get('end_time', '')
            # 时间格式化
            end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''
        except Exception as e:
            logger.info("用户输入的时间有误：\n{}".format(e))
            start_time = end_time = ''

        if start_time and not end_time:
            newses = newses.filter(update_time__gte=start_time)
        if end_time and not start_time:
            newses = newses.filter(update_time__lte=end_time)

        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))

        # 通过title进行过滤
        title = request.GET.get('title', '')
        if title:
            newses = newses.filter(title__icontains=title)

        # 通过作者名进行过滤
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)

        # 获取第几页内容
        try:
            # 获取前端的页码,默认是第一页
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info("当前页数错误：\n{}".format(e))
            page = 1
        paginator = Paginator(newses, constants.PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            news_info = paginator.page(paginator.num_pages)

        paginator_data = paginator_script.get_paginator_data(paginator, news_info)

        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if end_time else ''
        context = {
            'news_info': news_info,
            'tags': tags,
            'start_time': start_time,
            "end_time": end_time,
            "title": title,
            "author_name": author_name,
            "tag_id": tag_id,
            "other_param": urlencode({
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "author_name": author_name,
                "tag_id": tag_id,
            })
        }
        context.update(paginator_data)
        return render(request, 'admin/news/news_manage.html', context=context)


# 新闻编辑
class NewsEditView(View):
    """
    /admin/news/<int:new_id>/
    """
    def delete(self, request, news_id):
        """
        删除文章
        """
        news = models.News.objects.only('id').filter(id=news_id).first()
        if news:
            news.is_delete = True
            # 更新参数
            news.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='文章删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

    def get(self, request, news_id):
        """
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.filter(is_delete=False, id=news_id).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg="文章不存在")
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())

    def put(self, request, news_id):
        """
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.filter(id=news_id).first()
        # 验证参数
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg="文章不存在")
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.content = form.cleaned_data.get('content')
            news.image_url = form.cleaned_data.get('image_url')
            news.tag = form.cleaned_data.get('tag')
            news.save()
            return to_json_data(errmsg='文章更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 新闻发布
class NewsPubView(View):
    """
    /admin/news/pub/
    """

    def get(self, request):
        """"""
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())

    def post(self,request):
        # 1.从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 2.将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            # 3.保存到数据库
            # 只有form继承了forms.ModelForm 才能使用这种方法
            news_instance = form.save(commit=False)
            news_instance.author_id = request.user.id
            # news_instance.author_id = 1     # for test
            news_instance.save()
            # 4. 返回给前端
            return to_json_data(errmsg='文章创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 新闻升级
class NewsUploadImage(View):
    """"""

    def post(self, request):
        image_file = request.FILES.get('image_file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取图片失败')

        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件')

        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='图片上传到服务器失败')
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功')


# 七牛云token
class UploadToken(View):
    """
    """
    def get(self, request):
        access_key = qiniu_secret_info.QI_NIU_ACCESS_KEY
        secret_key = qiniu_secret_info.QI_NIU_SECRET_KEY
        bucket_name = qiniu_secret_info.QI_NIU_BUCKET_NAME
        # 构建鉴权对象
        q = qiniu.Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)

        return JsonResponse({"uptoken": token})


# 上传图片
class MarkDownUploadImage(View):
    """"""
    def post(self, request):
        image_file = request.FILES.get('editormd-image-file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return JsonResponse({'success': 0, 'message': '从前端获取图片失败'})

        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return JsonResponse({'success': 0, 'message': '不能上传非图片文件'})

        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return JsonResponse({'success': 0, 'message': '图片上传异常'})
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return JsonResponse({'success': 0, 'message': '图片上传到服务器失败'})
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return JsonResponse({'success': 1, 'message': '图片上传成功', 'url': image_url})


# 轮播图
class BannerManageView(View):
    """"""
    def get(self, request):
        banners = models.Banner.objects.only(
            'id', 'priority', 'image_url'
        ).filter(is_delete=False)
        priority_dict = {x:y for x,y in models.Banner().PRI_CHOICES}

        return render(request, 'admin/news/news_banner.html', locals())


# 编辑轮播图
class BannerEditView(View):
    """
     /admin/banners/<int:banner_id>/
    """

    def delete(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if banner:
            banner.is_delete = True
            banner.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='轮播图删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图不存在')

    def put(self, request, banner_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数不存在')
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误')
        except Exception as e:
            logger.info('轮播图优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误')

        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的轮播图不存在')
        if banner.priority == priority:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级优先级无变化')
        banner.priority = priority
        banner.save(update_fields=['priority', 'update_time'])
        return to_json_data(errmsg='轮播图更新成功')


# 新增轮播图
class BannerAddView(View):
    """"""
    def get(self, request):
        """
        :param request:
        :return:
        """
        tags = models.Tag.objects.select_related('news').values(
            'id', 'name'
        ).annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news')

        priority_dict = dict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_banner_add.html', locals())


    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 2.将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('热门文章：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误')
        except Exception as e:
            logger.info('热门文章：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        try:
            image_url = dict_data.get('image_url')
        except Exception as e:
            logger.info('图片url：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='图片上传错误')
        banner_tuple = models.Banner.objects.get_or_create(news_id=news_id)
        banner, is_created = banner_tuple
        banner.priority = priority
        banner.image_url = image_url
        banner.save()
        return to_json_data(errmsg='轮播图修改成功')


# 文章管理
class DocsManageView(View):
    """"""
    def get(self, request):
        docs = Doc.objects.only('title','update_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', locals())


# 文档编辑
class DocsEditView(View):
    """
    /admin/docs/<int:doc_id>/
    """
    def delete(self, request, doc_id):
        # 获取参数并验证
        doc = Doc.objects.only('id').filter(id=doc_id, is_delete=False).first()
        if doc:
            doc.is_delete = True
            # 更新参数
            doc.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='轮播图删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图不存在')

    def get(self, request, doc_id):
        doc = Doc.objects.only('id').filter(id=doc_id).first()
        if not doc:
            return to_json_data(errno=Code.PARAMERR, errmsg="文档不存在")
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/doc/docs_pub.html', locals())

    def put(self, request, doc_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数不存在')
        dict_data = json.loads(json_data.decode('utf8'))

        doc = Doc.objects.filter(id=doc_id, is_delete=False).first()
        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            doc.title = form.cleaned_data.get('title')
            doc.desc = form.cleaned_data.get('desc')
            doc.file_url = form.cleaned_data.get('file_url')
            doc.image_url = form.cleaned_data.get('image_url')
            doc.save()
            return to_json_data(errmsg='文档更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 文档发布
class DocsPubView(View):
    """
    /admin/docs/pub/
    """
    def get(self,request):
        return render(request, 'admin/doc/docs_pub.html')

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode("utf8"))
        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            # 3.保存到数据库
            # 只有form继承了forms.ModelForm 才能使用这种方法
            docs_instance = form.save(commit=False)
            docs_instance.author_id = request.user.id
            # news_instance.author_id = 1     # for test
            docs_instance.save()
            # 4. 返回给前端
            return to_json_data(errmsg='文档创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 文档上传
class DocsUploadView(View):
    """
    文档上传
    /admin/doc/files/
    """
    def post(self, request):
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败!')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取文件失败')
        if text_file.content_type not in ('application/octet-stream', 'application/pdf',
                                          'application/zip', 'text/plain', 'application/x-rar'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非正常文件')

        try:
            text_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('文件拓展名异常：{}'.format(e))
            text_ext_name = 'pdf'

        try:
            upload_res = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name=text_ext_name)
        except Exception as e:
            logger.error('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('文件上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='文件上传到服务器失败')
            else:
                text_name = upload_res.get('Remote file_id')
                text_url = settings.FASTDFS_SERVER_DOMAIN + text_name
                return to_json_data(data={'text_file': text_url}, errmsg='文件上传成功')


# 在线课堂管理
class CoursesManageView(View):
    """
    /admin/course/
    """
    def get(self, request):
        courses = Course.objects.all()
        return render(request, 'admin/course/courses_manage.html', locals())


# 课堂编辑
class CoursesEditView(View):
    """
    /admin/courses/<int:course_id>
    """
    def delete(self, request, course_id):
        """"""
        courses = Course.objects.only('id').filter(is_delete=False, id=course_id).first()
        if courses:
            courses.is_delete = True
            courses.save(update_field=['is_delete', 'update_time'])
            return to_json_data(errmsg="在线课堂删除成功")

    def get(self, request, course_id):
        """"""
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        teachers = Teacher.objects.all()
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        if not course:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        return render(request, 'admin/course/courses_pub.html', locals())

    def put(self, request, course_id):
        """"""
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode("utf8"))
        course = Course.objects.filter(id=course_id, is_delete=False).first()
        form = forms.CoursesPubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(course, attr, value)
            course.save()
            return to_json_data(errmsg='课程更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 课堂发布
class CoursesPubView(View):
    """
    /admin/courses/pub/
    """
    def get(self,request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request,'admin/course/courses_pub.html',locals())

    def post(self,request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.CoursesPubForm(data=dict_data)
        if form.is_valid():
            courses_instance = form.save()
            return to_json_data(errmsg='课程发布成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class GroupManageView(View):
    """"""
    def get(self, request):
        Group.objects.values('id', 'name').annotate(
            num_users=Count('user')
        ).order_by('-num_users', 'id')
        return render(request, 'admin/users/groups_manage.html', locals())


class GroupsEditView(View):
    """
    /admin/group/<int:group_di>/
    """
