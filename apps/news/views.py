from django.shortcuts import render
from django.views import View
from django.core.paginator import Paginator, EmptyPage
from time import strftime
from django.http import Http404

from news import models
from news import constants
from config.json_fun import to_json_data
from config.res_code import Code, error_map

import logging
import json
# Create your views here.

logger = logging.getLogger('django')


def index(request):
    return render(request,'news/index.html')

class IndexView(View):
    """
    主页视图: 127.0.0.1：8000
    """
    def get(self, request):
        # 数据库查询tag
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)

        # 数据库查询热门新闻
        hot_news = models.HotNews.objects.select_related('news').only(
            'news__title', 'news__image_url', 'news_id'
        ).filter(is_delete=False).order_by(
            'priority','-news__clicks'
        )[:constants.SHOW_HOTNEWS_COUNT]
        # tags = models.Tag.objects.defer('id', 'name').filter(is_delete=False) # 排除
        # context = {
        #     'tags': tags,
        # }
        return render(request, 'news/index.html', locals()) # locals()会将全部变量传输


class NewListView(View):
    """"""
    def get(self, request):
        # 1获取参数
        # 2校验参数
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.error('标签错误：\n{}'.format(e))
            tag_id = 0

        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.error('页面错误：\n{}'.format(e))
            page =1

        # 3数据库获取数据
        # title、digest、image_url、update_time
        # select_related
        news_queryset = models.News.objects.select_related('tag', 'author').only(
            'title', 'digest', 'image_url','update_time', 'tag__name', 'author__username')
        news = news_queryset.filter(is_delete=False, tag_id=tag_id) or news_queryset.filter(is_delete=False)

        # 4分页
        paginator = Paginator(news, constants.PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except Exception:
            logger.error('访问页面失败')
            news_info = paginator.page(paginator.num_pages)
        # 5序列化输出
        news_info_list = []
        for n in news_info:
            news_info_list.append({
                'id': n.id,
                'title': n.title,
                'digest': n.digest,
                'image_url': n.image_url,
                'update_time': n.update_time.strftime('%Y年%m月%d日 %H:%M'),
                'tag_name': n.tag.name,
                'author': n.author.username
                })
        data = {
            'news': news_info_list,
            'total_pages': paginator.num_pages
        }
        # 6返回数据到前端
        return to_json_data(data=data)


class NewsBanner(View):
    """"""
    def get(self, request):
        banners = models.Banner.objects.select_related('news').only(
            'image_url', 'news_id', 'news__title'
        ).filter(is_delete=False).order_by(
            'priority', '-news__clicks'
        )[:constants.SHOW_BANNER_COUNT]

        # 序列化输出
        banners_info_list = []
        for b in banners:
            banners_info_list.append(
                {
                    'image_url': b.image_url,
                    'news_id': b.news_id,
                    'news_title': b.news.title
                }
            )
        data = {
            'banners': banners_info_list
        }
        return to_json_data(data=data)


class NewsDetailView(View):
    """
    /news/<int:news_id>/

    """
    def get(self, request, news_id):
        # 数据库查询
        news = models.News.objects.select_related('tag', 'author').only(
            'title', 'content', 'update_time', 'tag__name', 'author__username'
        ).filter(is_delete=False, id=news_id).first()
        if news:
            # content, update_time, patent, username, parent.content, update_time
            comments = models.Comments.objects.select_related('author', 'parent').only(
                'content', 'update_time', 'author__username', 'parent__content',
                'parent__author__username', 'parent__update_time'
            ).filter(is_delete=False, news_id=news_id)
            comments_list = []
            # 拿出每一个评论
            for comm in comments:
                comments_list.append(comm.to_dict_data())
            return render(request, 'news/news_detail.html', locals())
        else:
            return Http404('新闻{}不存在'.format('news_id'))


class NewsCommentView(View):
    """
    /news/<int:news_id>/comments/
    """
    def post(self, request, news_id):
        # 1获取参数
        # 是否登录
        if not request.user.is_authenticated:
            return to_json_data(errno=Code.SESSIONERR, errmsg=error_map[Code.SESSIONERR])

        if not models.News.objects.only('id').filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='新闻不存在')

        json_data = request.body
        # 2校验参数
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        content = dict_data.get('content')
        if not content:
            return to_json_data(errno=Code.PARAMERR, errmsg='评论内容不能为空')
        # 提取父评论
        parent_id = dict_data.get('parent_id')
        # 验证父评论
        try:
            if parent_id:
                parent_id = int(parent_id)
                if not models.Comments.objects.only('id').filter(
                        is_delete=False, id=parent_id, news_id=news_id
                ).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        except Exception as e:
            logger.info('parent_id有误：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='parent_id异常')
        # 3存入数据
        news_comment = models.Comments()
        news_comment.content = content
        news_comment.news_id = news_id
        news_comment.author =request.user
        news_comment.parent_id = parent_id if parent_id else None
        news_comment.save()
        # 4返回前端
        return to_json_data(data=news_comment.to_dict_data())