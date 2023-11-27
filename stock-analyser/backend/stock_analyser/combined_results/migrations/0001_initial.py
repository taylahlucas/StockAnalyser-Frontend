# Generated by Django 3.1.7 on 2021-06-28 09:18

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('trends', '0001_initial'),
        ('stock_prices', '0001_initial'),
        ('financials', '0002_auto_20210628_0918'),
    ]

    operations = [
        migrations.CreateModel(
            name='CombinedResultsModel',
            fields=[
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('id', models.CharField(default=uuid.uuid4, max_length=100, primary_key=True, serialize=False)),
                ('asx_code', models.CharField(max_length=10)),
                ('company_name', models.CharField(blank=True, max_length=100)),
                ('financials', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='financials.financialsmodel')),
                ('stock_prices', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='stock_prices.stockpricemodel')),
                ('trends', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='trends.trendsmodel')),
            ],
        ),
    ]
