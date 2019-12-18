"""Copyright (c) 2018 Great Ormond Street Hospital for Children NHS Foundation
Trust & Birmingham Women's and Children's NHS Foundation Trust

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import requests
from bs4 import BeautifulSoup
import os
from .api_utils.poll_api import PollAPI
from .vep_utils import run_vep_batch
from .models import *
from .database_utils.multiple_case_adder import GeneManager, MultipleCaseAdder
from celery import task
import json
from json import JSONDecodeError
import labkey as lk
from datetime import datetime
import json
import time
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.palettes import Spectral8
from bokeh.plotting import figure
from django.core.mail import EmailMessage
from reversion.models import Version, Revision
from protocols.reports_6_0_0 import InterpretedGenome, InterpretationRequestRD, CancerInterpretationRequest, ClinicalReport
from django.utils import timezone
import csv
import xlsxwriter
from datetime import date
from django.db.models import Sum
import datetime
from django.contrib.auth.models import User, Group
from .sv_extraction.filter_sv import SVFiltration
import gc
from django.db.utils import ProgrammingError, OperationalError
import re


def create_admin_group():
    try:
        group, created = Group.objects.get_or_create(name='ADMIN GROUP')
        if not hasattr(group, 'grouppermissions'):
            group_permissions = GroupPermissions(group=group)
            group_permissions.save()
        permissions = group.grouppermissions
        permissions.cancer = True
        permissions.raredisease = True
        permissions.can_view_pvs = True
        permissions.can_view_svs = True
        permissions.can_view_strs = True
        permissions.can_select_update_transcript = True
        permissions.pull_t3_variants = True
        permissions.can_edit_proband = True
        permissions.can_edit_completed_proband = True
        permissions.can_edit_gelir = True
        permissions.can_edit_mdt = True
        permissions.can_get_gel_report = True
        permissions.can_edit_relative = True
        permissions.can_edit_clinical_questions = True
        permissions.start_mdt = True
        permissions.can_edit_case_alert = True
        permissions.can_edit_validation_list = True
        permissions.save()
    except (ProgrammingError, OperationalError):
        pass # Models probably don't exist yet
    try:
        gmc_list = Proband.objects.all().values_list('gmc', flat=True)
        gmc_list = set(gmc_list)
        for gmc in gmc_list:
            if gmc:
                GMC.objects.get_or_create(name=gmc)
    except (ProgrammingError, OperationalError):
        pass # Models probably don't exist yet


def get_gel_content(ir, ir_version):
    '''
    Downloads and formats the GEL Clinical Report. Removes warning signs and inserts the genes in the panel
    :param user_email: Logged in user email address
    :param ir: Interpretation report ID or CIP id
    :param ir_version: Version of CIP id
    :return: Beautiful soup version of the report
    '''
    # otherwise get uname and password from a file
    interpretation_reponse = PollAPI(
        "cip_api", f'interpretation-request/{ir}/{ir_version}/?reports_v6=true')
    interp_json = interpretation_reponse.get_json_response()

    analysis_versions = []
    latest = None
    if 'clinical_report' in interp_json:
        for clinical_report in interp_json['clinical_report']:
            analysis_versions.append(clinical_report['clinical_report_version'])
        try:
            latest = max(analysis_versions)
        except ValueError as e:
            latest = 1

    loop_over_reports = True
    while loop_over_reports:
        print(f"Using clinical report version {latest}")
        print(f"Using this endpoint: /clinical-report/{ir}/{ir_version}/{latest}")
        html_report = PollAPI(
            "cip_api", f"clinical-report/{ir}/{ir_version}/{latest}"
        )
        gel_content = html_report.get_json_response(content=True)
        try:
            gel_json_content = json.loads(gel_content)
            
            if gel_json_content['detail'].startswith('Not found') or gel_json_content['detail'].startswith(
                    'Method \"GET\" not allowed'):
                if latest == 1:
                    raise ValueError('No Clinical Report found for this case')
                else:
                    latest -= 1
            else:
                loop_over_reports = False
        except JSONDecodeError:
            loop_over_reports = False

    analysis_panels = {}

    panel_app_panel_query_version = 'https://panelapp.genomicsengland.co.uk/WebServices/get_panel/{panelhash}/?version={version}' # matches PollAPI 
    if 'pedigree' in interp_json['interpretation_request_data']['json_request']:
        if interp_json['interpretation_request_data']['json_request']['pedigree']['analysisPanels']:
            for panel_section in interp_json['interpretation_request_data']['json_request']['pedigree']['analysisPanels']:
                panel_name = panel_section['panelName']
                version = panel_section['panelVersion']
                analysis_panels[panel_name] = {}
                panel_details = requests.get(panel_app_panel_query_version.format(panelhash=panel_name, version=version),
                                             verify=False).json()
                analysis_panels[panel_name][panel_details['result']['SpecificDiseaseName']] = []
                try:
                    for gene in panel_details['result']['Genes']:
                        if gene['LevelOfConfidence'] == 'HighEvidence':
                            analysis_panels[panel_name][panel_details['result']['SpecificDiseaseName']].append(gene['GeneSymbol'])
                except KeyError:
                    pass
    
    gene_panels = {}
    for panel, details in analysis_panels.items():
        gene_panels.update(details)

    gel_content = BeautifulSoup(gel_content, 'lxml')
    try:
        # remove any warning signs if they appear in the report
        disclaimer = gel_content.find("div", {"class": "content-div error-panel"}).extract()
    except:
        pass
    # Find the annex header
    annex = gel_content.find("div", {"class": "annex-banner content-div"})

    # Add a div for the panels  Table tag to be inserted after the report annex
    div_tag = gel_content.new_tag("div")
    div_tag['class'] = "content-div"
    if annex:
        annex.insert_after(div_tag)

    # panel_keys = fake_panels.keys()
    panel_keys = list(gene_panels.keys())
    table_tag = gel_content.new_tag("table id='green_genes'")

    h3_tag = gel_content.new_tag("h3")
    h3_tag.string = 'Gene Panel Specification (Green Genes only)'

    # Table headers and table rows to be inserted after the table tag
    # tags created to shamelessly rip off the GeL formatting
    thead_tag = gel_content.new_tag("thead")
    tr_tag = gel_content.new_tag("tr")
    th1_tag = gel_content.new_tag("th")
    th2_tag = gel_content.new_tag("th")
    th3_tag = gel_content.new_tag("th")

    th1_tag.string = 'Gene Panel Name'
    th2_tag.string = 'Genes'
    th3_tag.string = 'Gene Panel Size'

    tr_tag.insert(1, th1_tag)
    tr_tag.insert(2, th2_tag)
    tr_tag.insert(3, th3_tag)
    thead_tag.insert(1, tr_tag)
    table_tag.insert(1, thead_tag)

    tbody_tag = gel_content.new_tag("tbody")

    # Sort panel keys based on gel report order
    gel_content_genepanels_order = []
    try:
        gel_content_genepanels_header = gel_content.find('h3',text="Gene Panels")
        for row in gel_content_genepanels_header.findNext('table').tbody.find_all('tr'):
            for link in row.find_all('a'):
                gel_content_genepanels_order.extend(link.contents)
        panel_keys = gel_content_genepanels_order
    except:
        pass

    for panel in range(len(panel_keys)):
        # get the actual name of the panel
        panel_name = panel_keys[panel]
        panel_genes = gene_panels[panel_name]
        panel_genes.sort()
        panel_gene_size = len(gene_panels[panel_name])

        tr_tag = gel_content.new_tag("tr")
        td_panel = gel_content.new_tag("td")
        td_panel['width'] = '20%'
        td_genes = gel_content.new_tag("td")
        td_panelsize = gel_content.new_tag("td")
        td_panelsize['width'] = '5%'

        td_panel.string = panel_name
        td_genes.string = ', '.join(panel_genes)
        td_panelsize.string = str(panel_gene_size)

        tr_tag.insert(1, td_panel)
        tr_tag.insert(2, td_genes)
        tr_tag.insert(3, td_panelsize)
        tbody_tag.insert(panel, tr_tag)

    table_tag.insert(2, tbody_tag)

    div_tag.insert(1, h3_tag)
    div_tag.insert(2, table_tag)

    # Remove gene size column (col3) from Gene Panels table, known bug at GeL
    pattern = re.compile(r'Gene Panels')
    table = gel_content.find('h3', text=pattern).findNext('table')
    new_header = table.thead.findAll('th')[0:2]
    
    table_tag = gel_content.new_tag("table id='panels'")
    thead_tag = gel_content.new_tag("thead")
    tr_tag = gel_content.new_tag("tr")
    th1_tag = gel_content.new_tag("th")
    th2_tag = gel_content.new_tag("th")
    tbody_tag = gel_content.new_tag("tbody")

    # New table headers
    th1_tag = new_header[0]
    th2_tag = new_header[1]
    tr_tag.insert(1, th1_tag)
    tr_tag.insert(2, th2_tag)
    thead_tag.insert(1, tr_tag)
    table_tag.insert(1, thead_tag)

    # New table rows
    row_pos = 1
    for row in table.tbody.findAll('tr'):
        tr_tag = gel_content.new_tag("tr")
        col1 = row.findAll('td')[0]
        col2 = row.findAll('td')[1]
        tr_tag.insert(1, col1)
        tr_tag.insert(1, col2)
        tbody_tag.insert(row_pos, tr_tag)
        row_pos += 1
    table_tag.insert(1, tbody_tag)
    
    table.replaceWith(table_tag)

    gel_content = gel_content.prettify()
    return gel_content


def panel_app(gene_panel, gp_version):
    '''
    Returns the list of genes associated with a panel in a dictionary which are then placed in the GEL clinical report
    :param gene_panel: PanelName
    :param gp_version: PanelVersion
    :return: Dict with gene list and len of gene list
    '''
    gene_list = []
    panel_app_panel_query_version = 'https://panelapp.genomicsengland.co.uk/WebServices/get_panel/{panelhash}/?version={version}'
    panel_details = requests.get(
        panel_app_panel_query_version.format(gene_panel=gene_panel, gp_version=gp_version), verify=False).json()

    for gene in panel_details['result']['Genes']:
        gene_list.append(gene['GeneSymbol'])
    gene_panel_info = {'gene_list': gene_list, 'panel_length': len(gene_list)}
    return gene_panel_info


def sv_extraction(writer, report_id):
    '''
    Takes the SV extraction package and ties it to a button
    :param report_id:
    :return:
    '''
    report = GELInterpretationReport.objects.get(id=report_id)
    ir, ir_version = report.ir_family.ir_family_id.split('-')
    SVFiltration(ir=ir, ir_version=ir_version, test_data=False)
    with open(f"output/{report.ir_family.ir_family_id}.supplementary.filtered_sv_table.csv") as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            writer.writerow(row)
    return writer


@task
def update_for_t3(report_id):
    '''
    Utility function designed to be run with celery.  Pulls T3 variants for a GEL Report
    :param report_id: GEL InterpretationReport ID
    :return: Nothing
    '''
    report = GELInterpretationReport.objects.get(id=report_id)
    MultipleCaseAdder(sample_type=report.sample_type,
                      pullt3=True,
                      sample=report.ir_family.participant_family.proband.gel_id)


@task
def report_export_for_rakib():
    rd_irs = GELInterpretationReport.objects.latest_cases_by_sample_type('raredisease')
    cancer_irs = GELInterpretationReport.objects.latest_cases_by_sample_type('cancer')
    output = open('GEL2MDT_export.csv', 'w')
    output.write('CIP ID,GEL Participant ID,Case Status,Disease,Disease subtype,LDP,SampleType\n')
    for q in rd_irs:
        try:
            output.write(f'{q.ir_family.ir_family_id},{q.ir_family.participant_family.proband.gel_id},'
                         f'{q.get_case_status_display()},{q.ir_family.participant_family.proband.recruiting_disease},'
                         f'{q.ir_family.participant_family.proband.disease_subtype},'
                         f'{q.ir_family.participant_family.proband.gmc},RareDisease\n')
        except Proband.DoesNotExist:
            pass
    for q in cancer_irs:
        try:
            output.write(f'{q.ir_family.ir_family_id},{q.ir_family.participant_family.proband.gel_id},'
                         f'{q.get_case_status_display()},{q.ir_family.participant_family.proband.recruiting_disease},'
                         f'{q.ir_family.participant_family.proband.disease_subtype},'
                         f'{q.ir_family.participant_family.proband.gmc},Cancer\n')
        except Proband.DoesNotExist:
            pass
    output.close()
    subject, from_email, to = f'GeL2MDT Case Export', 'root@localhost.e.amses.net', \
                              'rakib.miah1@nhs.net'
    text_content = f'Please see attached report'
    try:
        msg = EmailMessage(subject, text_content, from_email, [to])
        msg.attach_file("GEL2MDT_export.csv")
        msg.send()
        os.remove('GEL2MDT_export.csv')
    except Exception as e:
        print(e)


@task
def case_alert_email():
    '''
    Utility function designed to be run with celery. Emails GELTeam nightly about CaseAlert cases
    :param report_id: GEL InterpretationReport ID
    :return: Nothing
    '''
    sample_types = {'raredisease': False, 'cancer': False}
    matching_cases = {}
    for s_type in sample_types:
        case_alerts = CaseAlert.objects.filter(sample_type=s_type)
        gel_reports = GELInterpretationReport.objects.latest_cases_by_sample_type(
            sample_type=s_type).prefetch_related('ir_family__participant_family__proband')
        matching_cases[s_type] = {}
        for case in case_alerts:
            matching_cases[s_type][case.id] = []
            for report in gel_reports:
                try:
                    if report.ir_family.participant_family.proband.gel_id == str(case.gel_id):
                        matching_cases[s_type][case.id].append((report.id,
                                                                report.ir_family.ir_family_id))
                        sample_types[s_type] = True
                except Proband.DoesNotExist:
                    pass
    if sample_types['cancer'] or sample_types['raredisease']:
        text_content = "A Case Alert has been triggered, please visit GEL2MDT to check and remove this alert!"
        try:
            if sample_types['raredisease']:
                subject, from_email, to = f'GeL2MDT RD CaseAlert', 'root@localhost.e.amses.net', ['GELTeam@gosh.nhs.uk']
                msg = EmailMessage(subject, text_content, from_email, to)
                msg.send()
            if sample_types['cancer']:
                subject, from_email, to = f'GeL2MDT Cancer CaseAlert', 'root@localhost.e.amses.net', ['Laura.King3@gosh.nhs.uk',
                                                                                                      'Shazia.Mahamdallie@gosh.nhs.uk']
                msg = EmailMessage(subject, text_content, from_email, to)
                msg.send()
        except Exception as e:
            pass


@task
def listupdate_email():
    '''
    Utility function which sends emails to admin about last nights update
    :return:
    '''
    send = False
    bioinfo_content = 'Sample Type\tUpdate Time\tNo. Cases Added\tNo. Cases Updated\tError\n'
    for i, sample_type in enumerate(['raredisease', 'cancer']):
        listupdates = ListUpdate.objects.filter(update_time__gte=date.today()).filter(sample_type=sample_type)
        if listupdates:
            send = True
        for update in listupdates:
            bioinfo_content += f'{update.sample_type}\t{update.update_time}' \
                               f'\t{update.cases_added}\t{update.cases_updated}\t{update.error}\n'
    if send:
        subject, from_email, to = 'GeL2MDT ListUpdate', 'root@localhost.e.amses.net', \
                                  'bioinformatics@gosh.nhs.uk'
        msg = EmailMessage(subject, bioinfo_content, from_email, [to])
        try:
            msg.send()
        except Exception:
            pass

@task
def update_cases():
    '''
    Utility function designed to be run with celery as a replacement for a cronjob. Should be run every day to update
    the database with new cases
    :return:
    '''
    MultipleCaseAdder(sample_type='raredisease', bins=200, pullt3=False, skip_demographics=False)
    MultipleCaseAdder(sample_type='cancer', bins=200, pullt3=False, skip_demographics=False)
    gc.collect()


class VariantAdder(object):
    """
    Class for adding single variants to a case
    """
    def __init__(self, report, variant, variant_entry):
        self.report = report
        self.variant_entry = variant_entry
        self.variants = [variant]
        self.transcripts = None
        self.gene_manager = GeneManager
        self.gene_entries = []
        self.transcript_entries = []
        self.proband_variant = None
        self.pv_flag = None
        self.run_vep()
        self.insert_genes()
        self.insert_transcripts()
        self.insert_transcript_variants()
        self.insert_proband_variant()
        self.insert_proband_transcript_variant()
        self.add_pv_flag()

    def run_vep(self):
        self.transcripts = run_vep_batch.generate_transcripts(self.variants)

    def insert_genes(self):
        gene_list = []
        for transcript in self.transcripts:
            if transcript.gene_ensembl_id and transcript.gene_hgnc_id:
                gene_list.append({
                    'ensembl_id': transcript.gene_ensembl_id,
                    'hgnc_name': transcript.gene_hgnc_name,
                    'hgnc_id': str(transcript.gene_hgnc_id),
                })

        for gene in gene_list:
            p, created = Gene.objects.get_or_create(hgnc_id=gene['hgnc_id'],
                                                    defaults={'hgnc_name':gene['hgnc_name'],
                                                              'ensembl_id': gene['ensembl_id']})
            self.gene_entries.append(p)

    def insert_transcripts(self):
        for transcript in self.transcripts:
            # convert canonical to bools:
            transcript.canonical = transcript.transcript_canonical == "YES"
            if not transcript.gene_hgnc_id:
                # if the transcript has no recognised gene associated
                continue  # don't bother checking genes
            transcript.gene_model = None
            for gene in self.gene_entries:
                if gene.hgnc_id == transcript.gene_hgnc_id:
                    transcript.gene_model = gene

            for transcript in self.transcripts:
                if transcript.gene_model:
                    p, created = Transcript.objects.get_or_create(name=transcript.transcript_name,
                                                                  genome_assembly=self.report.assembly,
                                                                  defaults={'gene': transcript.gene_model,
                                                                            'canonical_transcript':transcript.canonical,
                                                                            'strand': transcript.transcript_strand
                                                                            })
                    self.transcript_entries.append(p)

    def insert_transcript_variants(self):
        for transcript in self.transcripts:
            transcript.variant_entry = self.variant_entry

            # add the corresponding Transcript entry
            for transcript_entry in self.transcript_entries:
                found = False
                if transcript_entry.name == transcript.transcript_name and transcript_entry.genome_assembly == self.report.assembly:
                    transcript.transcript_entry = transcript_entry
                    found = True
                    break
                if not found:
                    # we don't make entries for tx with no Gene
                    transcript.transcript_entry = None
        for transcript in self.transcripts:
            if transcript.transcript_entry:
                p, created = TranscriptVariant.objects.get_or_create(transcript=transcript.transcript_entry,
                                                                     variant=transcript.variant_entry,
                                                                     defaults={'af_max': transcript.gene_model,
                                                                        "af_max": transcript.transcript_variant_af_max,
                                                                        "hgvs_c": transcript.transcript_variant_hgvs_c,
                                                                        "hgvs_p": transcript.transcript_variant_hgvs_p,
                                                                        "hgvs_g": transcript.transcript_variant_hgvs_g,
                                                                        "sift": transcript.variant_sift,
                                                                        "polyphen": transcript.variant_polyphen})

    def insert_proband_variant(self):
        p, created = ProbandVariant.objects.get_or_create(
            interpretation_report=self.report,
            variant=self.variant_entry,
            defaults={"max_tier": 0,
                        "zygosity": "unknown",
                        "maternal_zygosity": "unknown",
                        "paternal_zygosity": "unknown",
                        "inheritance": "unknown",
                        "somatic": False})
        self.proband_variant = p

    def insert_proband_transcript_variant(self):
        for transcript in self.transcripts:
            if self.proband_variant.variant == transcript.variant_entry:
                transcript.proband_variant_entry = self.proband_variant
        for transcript in self.transcripts:
            if transcript.transcript_entry and transcript.proband_variant_entry:
                p, created = ProbandTranscriptVariant.objects.get_or_create(transcript=transcript.transcript_entry,
                                                                            proband_variant=transcript.proband_variant_entry,
                                                                     defaults={"selected": transcript.transcript_entry.canonical_transcript,
                                                                                "effect": transcript.proband_transcript_variant_effect})

    def add_pv_flag(self):
        self.pv_flag, created = PVFlag.objects.get_or_create(proband_variant=self.proband_variant,
                                                             flag_name='Manually Added')


class UpdateDemographics(object):
    '''
    Repolls labkey for a case. Should not be visible to all users due to labkey issues
    '''
    def __init__(self, report_id):
        self.report = GELInterpretationReport.objects.get(id=report_id)
        self.clinician = None
        config_dict = load_config.LoadConfig().load()
        # poll labkey
        if self.report.sample_type == 'raredisease':
            labkey_server_request = config_dict['labkey_server_request']
            self.server_context = lk.utils.create_server_context(
                'gmc.genomicsengland.nhs.uk',
                labkey_server_request,
                '/labkey', use_ssl=True)
        elif self.report.sample_type == 'cancer':
            labkey_server_request = config_dict['labkey_cancer_server_request']
            self.server_context = lk.utils.create_server_context(
                'gmc.genomicsengland.nhs.uk',
                labkey_server_request,
                '/labkey', use_ssl=True)

    def update_clinician(self):
        clinician_details = {}
        if self.report.sample_type=='raredisease':
            search_results = lk.query.select_rows(
                server_context=self.server_context,
                schema_name='gel_rare_diseases',
                query_name='rare_diseases_registration',
                filter_array=[
                    lk.query.QueryFilter('family_id',
                                         self.report.ir_family.participant_family.gel_family_id,
                                         'contains')
                ]
            )
        elif self.report.sample_type=='cancer':
            search_results = lk.query.select_rows(
                server_context=self.server_context,
                schema_name='gel_cancer',
                query_name='cancer_registration',
                filter_array=[
                    lk.query.QueryFilter('participant_identifiers_id',
                                         self.report.ir_family.participant_family.proband.gel_id,
                                         'contains')
                ]
            )
        try:
            clinician_details['name'] = search_results['rows'][0].get(
                'consultant_details_full_name_of_responsible_consultant')
        except IndexError as e:
            pass
        try:
            clinician_details['hospital'] = search_results['rows'][0].get(
                'consultant_details_hospital_of_responsible_consultant')
        except IndexError as e:
            pass

        if 'name' in clinician_details and 'hospital' in clinician_details:
            print(clinician_details)
            clinician = Clinician.objects.filter(
                name=clinician_details['name'],
                hospital = clinician_details['hospital']).first() # can return multiple if clinician as upper and lower case
            
            if clinician is None:
                clinician = Clinician.objects.create(
                    name=clinician_details['name'],
                    hospital = clinician_details['hospital'])

            self.clinician = clinician
            family = self.report.ir_family.participant_family
            family.clinician = clinician
            family.save()
            return clinician
        else:
            return None

    def update_demographics(self):
        participant_demographics = {
            "surname": 'unknown',
            "forename": 'unknown',
            "date_of_birth": '2011/01/01',  # unknown but needs to be in date format
            "nhs_num": 'unknown',
        }

        if self.report.sample_type == 'cancer':
            schema = 'gel_cancer'
        elif self.report.sample_type == 'raredisease':
            schema = 'gel_rare_diseases'
        search_results = lk.query.select_rows(
            server_context=self.server_context,
            schema_name=schema,
            query_name='participant_identifier',
            filter_array=[
                lk.query.QueryFilter(
                    'participant_id', self.report.ir_family.participant_family.proband.gel_id, 'contains')
            ]
        )
        try:
            participant_demographics["surname"] = search_results['rows'][0].get(
                'surname')
        except IndexError as e:
            pass
        try:
            participant_demographics["forename"] = search_results['rows'][0].get(
                'forenames')
        except IndexError as e:
            pass
        try:
            participant_demographics["date_of_birth"] = search_results['rows'][0].get(
                'date_of_birth').split(' ')[0]
        except IndexError as e:
            pass

        try:
            if self.report.sample_type == 'raredisease':
                if search_results['rows'][0].get('person_identifier_type').upper() == "NHSNUMBER":
                    participant_demographics["nhs_num"] = search_results['rows'][0].get(
                        'person_identifier')
            elif self.report.sample_type == 'cancer':
                participant_demographics["nhs_num"] = search_results['rows'][0].get(
                    'person_identifier')
        except IndexError as e:
            pass

        recruiting_disease = None
        if self.report.sample_type == 'raredisease':
            schema_name = 'gel_rare_diseases',
            query_name = 'rare_diseases_diagnosis'
        elif self.report.sample_type == 'cancer':
            schema_name = 'gel_cancer',
            query_name = 'cancer_diagnosis'
        search_results = lk.query.select_rows(
            server_context=self.server_context,
            schema_name=schema_name,
            query_name=query_name,
            filter_array=[
                lk.query.QueryFilter('participant_identifiers_id',
                                     self.report.ir_family.participant_family.proband.gel_id, 'eq')
            ]
        )
        try:
            if self.report.sample_type == 'raredisease':
                recruiting_disease = search_results['rows'][0].get('gel_disease_information_specific_disease', None)
            elif self.report.sample_type == 'cancer':
                recruiting_disease = search_results['rows'][0].get('diagnosis_icd_code', None)
        except IndexError as e:
            pass

        if participant_demographics['surname'] != 'unknown' and participant_demographics['nhs_num'] != 'unknown':
            proband = self.report.ir_family.participant_family.proband
            proband.nhs_number = participant_demographics['nhs_num']
            proband.surname = participant_demographics['surname']
            proband.forename = participant_demographics['forename']
            proband.date_of_birth = datetime.datetime.strptime(participant_demographics["date_of_birth"],
                                                               "%Y/%m/%d").date()
            proband.recruiting_disease = recruiting_disease
            proband.gmc = self.clinician.hospital
            proband.save()
            return proband
        else:
            return None


class UpdaterFromStorage:
    '''
    Utility class to allow you to use the local jsons to insert something new into the database
    Done for gel_sequence_id but will obviously need to be edited for any other value
    '''

    def __init__(self, sample_type):
        self.reports = GELInterpretationReport.objects.latest_cases_by_sample_type(sample_type).prefetch_related(
            *[
                'ir_family',
                'ir_family__participant_family__proband'
            ]
        )
        config_dict = load_config.LoadConfig().load()
        self.cip_api_storage = config_dict['cip_api_storage']
        for report in self.reports:
            self.json = self.load_json_data(report)
            if self.json:
                self.json_case_data = self.json["interpretation_request_data"]
                self.json_request_data = self.json_case_data["json_request"]
                if sample_type == 'raredisease':
                    self.ir_obj = InterpretationRequestRD.fromJsonDict(self.json_request_data)
                elif sample_type == 'cancer':
                    self.ir_obj = CancerInterpretationRequest.fromJsonDict(self.json_request_data)
                if self.ir_obj.workspace:
                    print(report, self.ir_obj.workspace)
                    workspace = self.ir_obj.workspace[0]
                    self.insert_into_db(report, workspace)

    def load_json_data(self, report):
        '''
        :return: Dict with key as CIPid and value as value_of_interest
        '''
        json_path = os.path.join(self.cip_api_storage, '{}.json'.format(report.ir_family.ir_family_id +  "-" +  str(report.archived_version)))
        if os.path.isfile(json_path):
            with open(json_path, 'r') as f:
                return json.load(f)
        else:
            return None

    def get_proband_json(self):
        """
        Get the proband from the list of partcipants in the JSON.
        """
        proband_json = None
        if self.json["sample_type"]=='raredisease':
            participant_jsons = \
                self.json_case_data["json_request"]["pedigree"]["participants"]
            for participant in participant_jsons:
                if participant["isProband"]:
                    proband_json = participant
        elif self.json["sample_type"]=='cancer':
            proband_json = self.json_case_data["json_request"]["cancerParticipant"]
        return proband_json

    def get_gel_sequence_id(self):
        proband_sample = None
        if self.json["sample_type"] == 'raredisease':
            proband_sample = self.proband["samples"][0]
        elif self.json["sample_type"] == 'cancer':
            proband_sample = self.proband["matchedSamples"][0]['tumourSampleId']
        return proband_sample

    def insert_into_db(self, report, workspace):
        try:
            proband = report.ir_family.participant_family.proband
            proband.gmc = workspace
            proband.save()
        except Proband.DoesNotExist:
            pass



def create_bokeh_barplot(names, values, title):
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

    source = ColumnDataSource(data=dict(names=names,
                                        counts=values, color=Spectral8))

    plot = figure(x_range=names, plot_height=350, plot_width=770, title=title,
                          tools=TOOLS)

    labels = LabelSet(x='names', y='counts', text='counts', level='glyph',
                      x_offset=-13.5, y_offset=0, source=source, render_mode='canvas')
    plot.vbar(x='names', top='counts', width=0.9, color='color', source=source)
    plot.add_layout(labels)
    plot.xgrid.grid_line_color = None
    plot.legend.orientation = "horizontal"
    plot.legend.location = "top_center"
    return plot


class ReportHistoryFormatter:
    def __init__(self, report):
        self.report = report
        self.proband = report.ir_family.participant_family.proband
        self.proband_history = Version.objects.get_for_object(self.proband).reverse()
        self.report_history = Version.objects.get_for_object(report).reverse()
        self.report_interesting_fields = ['assigned_user', 'case_sent', 'case_status', 'mdt_status', 'pilot_case',
                                          'no_primary_findings']
        self.proband_interesting_fields = ['forename', 'surname','date_of_birth','nhs_number','sex','outcome','comment',
                                           'discussion','action','gmc','lab_number','local_id','deceased','disease_group',
                                           'recruiting_disease','disease_subtype','disease_stage','disease_grade',
                                           'currently_in_clinical_trial','current_clinical_trial_info',
                                           'suitable_for_clinical_trial','previous_testing','previous_treatment']

    def get_report_history(self):
        for count, history in enumerate(self.report_history):
            history.serialized_data = json.loads(history.serialized_data)
            case_status_choices = dict(GELInterpretationReport._meta.get_field('case_status').choices)
            mdt_status_choices = dict(GELInterpretationReport._meta.get_field('mdt_status').choices)
            history.serialized_data[0]['fields']['case_status'] = case_status_choices[
                history.serialized_data[0]['fields']['case_status']]
            history.serialized_data[0]['fields']['mdt_status'] = mdt_status_choices[
                history.serialized_data[0]['fields']['mdt_status']]
            if count == 0:
                history.diff = (True, self.report_interesting_fields)
            else:
                diff_fields = self.json_diff(previous_history, history.serialized_data, self.report_interesting_fields)
                history.diff = diff_fields
            previous_history = history.serialized_data
        return self.report_history

    def get_proband_history(self):
        for count, history in enumerate(self.proband_history):
            history.serialized_data = json.loads(history.serialized_data)
            if count == 0:
                history.diff = (True, self.proband_interesting_fields)
            else:
                diff_fields = self.json_diff(previous_history, history.serialized_data, self.proband_interesting_fields)
                history.diff = diff_fields
            previous_history = history.serialized_data

        return self.proband_history

    @staticmethod
    def json_diff(most_recent_history, older_history, fields_of_interest):
        '''
        # Goes in decending order through json history and decides which fields to keep
        # Don't delete the first version
        :param version_list: list of json history
        :param fields_of_interest: all fields which will be displayed to the user
        :return: Tuple of (Boolean, [Fields to keep]
        '''
        new_subset = {k: most_recent_history[0]['fields'].get(k, None) for k in fields_of_interest}
        old_subset = {k: older_history[0]['fields'].get(k, None) for k in fields_of_interest}
        if new_subset == old_subset:
            return False, []
        else:
            field_diff = []
            for field in new_subset:
                if new_subset[field] != old_subset[field]:
                    field_diff.append(field)
            return True, field_diff

def email_admin_on_registration(registered, first_name, last_name, username):
    '''
    Send email of successful user registration to admin team.
    params: registered: boolean
    params: user requesting registration
    '''
    if registered:
        subject, from_email, to = f'GeL2MDT new user registered: {username}', 'root@localhost.e.amses.net', 'bioinformatics@gosh.nhs.uk'
        text_content = (f'New user registered:\n\n'
                        f'First name: {first_name}\n'
                        f'Last name: {last_name}\n'
                        f'Username: {username}\n')
        try:
            msg = EmailMessage(subject, text_content, from_email, [to])
            msg.send()
        except Exception as e:
            print(e)
