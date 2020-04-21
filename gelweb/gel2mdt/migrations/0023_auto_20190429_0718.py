# Generated by Django 2.0.13 on 2019-04-29 07:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0009_alter_user_last_name_max_length'),
        ('gel2mdt', '0022_auto_20190228_0803'),
    ]

    operations = [
        migrations.CreateModel(
            name='GMC',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'GMC',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='GroupPermissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancer', models.BooleanField(default=False, help_text='Indicates whether the group can view Cancer Cases')),
                ('raredisease', models.BooleanField(default=False, help_text='Indicates whether the group can view Rare Disease Cases')),
                ('can_view_pvs', models.BooleanField(default=False, help_text='Indicates whether the group can view Proband Variants ')),
                ('can_view_svs', models.BooleanField(default=False, help_text='Indicates whether the group can view Proband Structural Variants ')),
                ('can_view_strs', models.BooleanField(default=False, help_text='Indicates whether the group can view Proband STRs')),
                ('can_select_update_transcript', models.BooleanField(default=False, help_text='Indicates whether the group can update transcripts and select preferred Transcripts')),
                ('pull_t3_variants', models.BooleanField(default=False, help_text='Indicates whether the group can Pull T3 Variants')),
                ('can_edit_proband', models.BooleanField(default=False, help_text='Indicates whether the group can edit proband Information')),
                ('can_edit_completed_proband', models.BooleanField(default=False, help_text='Indicates whether the group can view & edit a Completed Proband')),
                ('can_edit_gelir', models.BooleanField(default=False, help_text='Indicates whether the group can edit Case information')),
                ('can_edit_mdt', models.BooleanField(default=False, help_text='Indicates whether the group can edit MDT questions')),
                ('can_get_gel_report', models.BooleanField(default=False, help_text='Indicates whether the group can pull the GEL report')),
                ('can_edit_relative', models.BooleanField(default=False, help_text='Indicates whether the group can edit relative information')),
                ('can_edit_clinical_questions', models.BooleanField(default=False, help_text='Indicates whether the group can edit cancer clinical questions')),
                ('start_mdt', models.BooleanField(default=False, help_text='Indicates whether the group can start MDTs')),
                ('can_edit_case_alert', models.BooleanField(default=False, help_text='Indicates whether the group can view & edit Case Alerts')),
                ('can_edit_validation_list', models.BooleanField(default=False, help_text='Indicates whether the group can view & edit the validation list')),
                ('gmc', models.ManyToManyField(to='gel2mdt.GMC')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
            ],
            options={
                'db_table': 'GroupPermissions',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ProbandSTR',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_tier', models.CharField(max_length=20, null=True)),
                ('proband_copies_a', models.IntegerField(null=True)),
                ('proband_copies_b', models.IntegerField(null=True)),
                ('maternal_copies_a', models.IntegerField(null=True)),
                ('maternal_copies_b', models.IntegerField(null=True)),
                ('paternal_copies_a', models.IntegerField(null=True)),
                ('paternal_copies_b', models.IntegerField(null=True)),
                ('mode_of_inheritance', models.CharField(max_length=128, null=True)),
                ('segregation_pattern', models.CharField(max_length=128, null=True)),
                ('requires_validation', models.BooleanField(db_column='Requires_Validation', default=False)),
                ('validation_status', models.CharField(choices=[('U', 'Unknown'), ('A', 'Awaiting Validation'), ('K', 'Urgent Validation'), ('I', 'In Progress'), ('P', 'Passed Validation'), ('F', 'Failed Validation'), ('N', 'Not Required')], default='U', max_length=50)),
                ('validation_datetime_set', models.DateTimeField(default=None, null=True)),
            ],
            options={
                'db_table': 'ProbandSTR',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ProbandSTRGene',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected', models.BooleanField(default=False)),
                ('gene', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.Gene')),
                ('proband_str', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.ProbandSTR')),
            ],
            options={
                'db_table': 'ProbandSTRGene',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ProbandSV',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('validation_status', models.CharField(choices=[('U', 'Unknown'), ('A', 'Awaiting Validation'), ('K', 'Urgent Validation'), ('I', 'In Progress'), ('P', 'Passed Validation'), ('F', 'Failed Validation'), ('N', 'Not Required')], default='U', max_length=4)),
                ('validation_datetime_set', models.DateTimeField(default=None, null=True)),
                ('max_tier', models.CharField(max_length=20, null=True)),
                ('cnv_af', models.FloatField(null=True)),
                ('cnv_auc', models.FloatField(null=True)),
            ],
            options={
                'db_table': 'ProbandSV',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ProbandSVGene',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected', models.BooleanField(default=False)),
                ('gene', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.Gene')),
                ('proband_sv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.ProbandSV')),
            ],
            options={
                'db_table': 'ProbandSVGene',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='STRVariant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chromosome', models.CharField(max_length=5)),
                ('str_start', models.IntegerField()),
                ('str_end', models.IntegerField()),
                ('repeated_sequence', models.CharField(max_length=32)),
                ('normal_threshold', models.IntegerField()),
                ('pathogenic_threshold', models.IntegerField()),
                ('genome_assembly', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gel2mdt.ToolOrAssemblyVersion')),
            ],
            options={
                'db_table': 'STRVariant',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SV',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant_type', models.CharField(choices=[('i', 'insertion'), ('p', 'duplication'), ('v', 'inversion'), ('a', 'amplification'), ('d', 'deletion'), ('t', 'tandem_duplication'), ('dm', 'deletion_mobile_element'), ('im', 'insertion_mobile_element')], max_length=40)),
            ],
            options={
                'db_table': 'SV',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SVRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chromosome', models.CharField(max_length=5)),
                ('sv_start', models.IntegerField()),
                ('sv_end', models.IntegerField()),
                ('genome_assembly', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gel2mdt.ToolOrAssemblyVersion')),
            ],
            options={
                'db_table': 'SVRegion',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='mdt',
            name='actions_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mdt',
            name='data_request_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mdt',
            name='gtab_made',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mdt',
            name='gtab_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='gelinterpretationreport',
            name='case_code',
            field=models.CharField(blank=True, choices=[('REANALYSE', 'REANALYSE'), ('URGENT', 'URGENT'), ('SAMPLE', 'SAMPLE'), ('CLINGEN', 'CLINGEN'), ('DECEASED', 'DECEASED'), ('DNAREQ', 'DNAREQ'), ('RETURN', 'RETURN')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='proband',
            name='gmc',
            field=models.CharField(blank=True, default='Unknown', max_length=255),
        ),
        migrations.AlterField(
            model_name='rarediseasereport',
            name='proband_variant',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.ProbandVariant'),
        ),
        migrations.AddField(
            model_name='sv',
            name='sv_region1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='region1', to='gel2mdt.SVRegion'),
        ),
        migrations.AddField(
            model_name='sv',
            name='sv_region2',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='region2', to='gel2mdt.SVRegion'),
        ),
        migrations.AddField(
            model_name='probandsv',
            name='interpretation_report',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.GELInterpretationReport'),
        ),
        migrations.AddField(
            model_name='probandsv',
            name='sv',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.SV'),
        ),
        migrations.AddField(
            model_name='probandsv',
            name='validation_responsible_user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='probandstr',
            name='interpretation_report',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.GELInterpretationReport'),
        ),
        migrations.AddField(
            model_name='probandstr',
            name='str_variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.STRVariant'),
        ),
        migrations.AddField(
            model_name='probandstr',
            name='validation_responsible_user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='rarediseasereport',
            name='proband_str',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.ProbandSTR'),
        ),
        migrations.AddField(
            model_name='rarediseasereport',
            name='proband_sv',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='gel2mdt.ProbandSV'),
        ),
        migrations.AlterUniqueTogether(
            name='svregion',
            unique_together={('chromosome', 'sv_start', 'sv_end', 'genome_assembly')},
        ),
        migrations.AlterUniqueTogether(
            name='sv',
            unique_together={('sv_region1', 'sv_region2', 'variant_type')},
        ),
        migrations.AlterUniqueTogether(
            name='strvariant',
            unique_together={('chromosome', 'str_start', 'str_end', 'genome_assembly', 'repeated_sequence', 'normal_threshold', 'pathogenic_threshold')},
        ),
        migrations.AlterUniqueTogether(
            name='probandsvgene',
            unique_together={('proband_sv', 'gene')},
        ),
        migrations.AlterUniqueTogether(
            name='probandsv',
            unique_together={('sv', 'interpretation_report')},
        ),
        migrations.AlterUniqueTogether(
            name='probandstrgene',
            unique_together={('proband_str', 'gene')},
        ),
        migrations.AlterUniqueTogether(
            name='probandstr',
            unique_together={('str_variant', 'interpretation_report')},
        ),
    ]