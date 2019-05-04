from django.views import View
from django.conf import settings
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.utils.encoding import escape_uri_path

from .models import Doc

import requests
import logging

logger = logging.getLogger('django')
# Create your views here.
def doc_index(request):
    """
    :param request:
    :return:
    """
    docs = Doc.objects.defer('author', 'create_time', 'update_time', 'is_delete').filter(
        is_delete=False
    )
    return render(request, 'doc/docDownload.html', locals())

class DocDownload(View):
    """
    /doc/<int:doc_id>/
    """
    def get(self, request, doc_id):
        doc = Doc.objects.only('file_url').filter(is_delete=False, id=doc_id).first()
        if doc:
            doc_url = settings.SITE_DOMAIN_PORT + doc.file_url
            try:
                file = requests.get(doc_url, stream=True)
                res = FileResponse(file)
            except Exception as e:
                logger.info('文档获取异常')
                raise Http404('文档获取异常')
            ex_name = doc_url.split('.')[-1]
            if not ex_name:
                raise Http404('文档url异常')
            else:
                ex_name = ex_name.lower()
            if ex_name == "pdf":
                res["Content-type"] = "application/pdf"
            elif ex_name == "zip":
                res["Content-type"] = "application/zip"
            elif ex_name == "doc":
                res["Content-type"] = "application/msword"
            elif ex_name == "xls":
                res["Content-type"] = "application/vnd.ms-excel"
            elif ex_name == "docx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ex_name == "ppt":
                res["Content-type"] = "application/vnd.ms-powerpoint"
            elif ex_name == "pptx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

            else:
                raise Http404("文档格式不正确！")

            doc_filename = escape_uri_path(doc_url.split('/')[-1])
            # http1.1 中的规范
            # 设置为inline，会直接打开
            # attachment 浏览器会开始下载
            res["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(doc_filename)
            return res

        else:
            raise Http404("文档不存在！")
