# Generated by Django 2.1.7 on 2019-04-26 02:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0002_auto_20190426_1038'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comments',
            name='priority',
        ),
    ]