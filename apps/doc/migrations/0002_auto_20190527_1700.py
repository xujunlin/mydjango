# Generated by Django 2.1 on 2019-05-27 09:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('doc', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='doc',
            name='author',
        ),
        migrations.DeleteModel(
            name='Doc',
        ),
    ]