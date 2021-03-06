# Generated by Django 2.0.1 on 2018-04-26 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gel2mdt', '0012_auto_20180423_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='gelinterpretationreport',
            name='case_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='gelinterpretationreport',
            name='case_status',
            field=models.CharField(choices=[('N', 'Not Started'), ('U', 'Under Review'), ('M', 'Awaiting MDT'), ('V', 'Awaiting Validation'), ('R', 'Awaiting Reporting'), ('P', 'Reported'), ('C', 'Completed'), ('E', 'External')], default='N', max_length=50),
        ),
        migrations.AddField(
            model_name='gelinterpretationreport',
            name='mdt_status',
            field=models.CharField(choices=[('U', 'Unknown'), ('R', 'Required'), ('N', 'Not Required'), ('I', 'In Progress'), ('D', 'Done')], default='U', max_length=50),
        ),
        migrations.AddField(
            model_name='gelinterpretationreport',
            name='pilot_case',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='proband',
            name='lab_number',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='proband',
            name='mdt_status',
            field=models.CharField(choices=[('U', 'Unknown'), ('R', 'Required'), ('N', 'Not Required'), ('I', 'In Progress'), ('D', 'Done')], default='U', max_length=50),
        ),
    ]
