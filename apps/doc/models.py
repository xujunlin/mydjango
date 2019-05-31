from django.db import models
from config.models import ModelBase
# Create your models here.


class Doc(ModelBase):
    """
    create doc view
    """
    file_url = models.URLField(verbose_name='文件url', help_text='文件URL')
    title = models.CharField(max_length=150, verbose_name='文档标题', help_text='文档标题')
    desc = models.TextField(verbose_name='文件描述', help_text='文件描述')
    image_url = models.URLField(default='', verbose_name='图片URL', help_text='图片URL')
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'tb_docs'
        verbose_name = '文档'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title