# Generated by Django 5.1.6 on 2025-03-01 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0003_alter_bankaccount_options_alter_company_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='graphic_element',
            field=models.ImageField(blank=True, null=True, upload_to='companies/graphic_elements/', verbose_name='graphic element'),
        ),
        migrations.AddField(
            model_name='company',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='companies/logos/', verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='bic',
            field=models.CharField(blank=True, default='', max_length=11, verbose_name='BIC'),
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='iban',
            field=models.CharField(max_length=34, verbose_name='IBAN'),
        ),
    ]
