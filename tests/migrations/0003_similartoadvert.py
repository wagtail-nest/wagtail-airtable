# Generated by Django 3.0.6 on 2020-05-15 18:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0002_modelnotused'),
    ]

    operations = [
        migrations.CreateModel(
            name='SimilarToAdvert',
            fields=[
                ('advert_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tests.Advert')),
            ],
            options={
                'abstract': False,
            },
            bases=('tests.advert',),
        ),
    ]
