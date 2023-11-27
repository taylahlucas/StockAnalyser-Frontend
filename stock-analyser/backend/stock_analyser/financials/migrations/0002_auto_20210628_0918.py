# Generated by Django 3.1.7 on 2021-06-28 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financials', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='financialsmodel',
            name='bv',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='company_name',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='current_stock_price',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='debt_equity',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='diluted_eps',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='dividend_payout',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='ebitda',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='eps',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='ev',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='ev_ebitda',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='ev_revenue',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='levered_cash_flow',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='operating_cash_flow',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='operating_margin',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='price_to_book',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='price_to_sales',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='profit_margin',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='return_on_equity',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='financialsmodel',
            name='trailing_pe',
            field=models.TextField(blank=True),
        ),
    ]
