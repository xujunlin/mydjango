import json
import logging
from datetime import datetime
from urllib.parse import urlencode


from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count
from django.shortcuts import render
from django.views import View

from doc.models import Doc
from news import models
from config.json_fun import to_json_data
from config.res_code import Code, error_map
from config import paginator_script
from admin import constants
from mysite import settings
from config.fastdfs.fdfs import FDFS_Client

logger = logging.getLogger('django')
# Create your views here.

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


class NewsManageView(View):
    """"""
# 请求方式：get
# 携带参数：start_time, end_time title, author_name, tag_id
# 返回参数：title, author_username, tag_name, update_time, id
    def get(self, request):
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


class NewsPubView(View):
    """
    /admin/news/pub/
    """

    def get(self, request):
        """"""
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())


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


class BannerManageView(View):
    """"""
    def get(self, request):
        banners = models.Banner.objects.only(
            'id', 'priority', 'image_url'
        ).filter(is_delete=False)
        priority_dict = {x:y for x,y in models.Banner().PRI_CHOICES}

        return render(request, 'admin/news/news_banner.html', locals())


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
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
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


class BannerAddView(View):
    """"""
    def get(self, request):
        tags = models.Tag.objects.select_related('news').values(
            'id', 'name'
        ).annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news')

        priority_dict = dict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_banner_add.html', locals())


class DocsManageView(View):
    """"""
    def get(self, request):
        docs = Doc.objects.only('title','update_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', locals())


class DocsEditView(View):
    """"""
    """
    /admin/docs/<int:banner_id>/
    """
    def delete(self, request, banner_id):
        # 获取参数并验证
        doc = Doc.objects.only('id').filter(id=banner_id).first()
        if doc:
            doc.is_delete = True
            # 更新参数
            doc.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='轮播图删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图不存在')



