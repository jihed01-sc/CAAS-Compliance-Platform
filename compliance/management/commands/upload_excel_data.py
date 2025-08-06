import pandas as pd
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from compliance.models import Framework, ControlCategory, Control


class Command(BaseCommand):
    help = 'Upload and process Excel files to update compliance framework data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mapping-matrix',
            type=str,
            required=True,
            help='C:\Users\Jihed\Downloads\TheMappin_Matrix (1).xlsx'
        )
        parser.add_argument(
            '--unified-referentiel',
            type=str,
            required=True,
            help='C:\Users\Jihed\Downloads\référentiel unifié.xlsx'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before importing'
        )

    def handle(self, *args, **options):
        mapping_file = options['mapping_matrix']
        unified_file = options['unified_referentiel']
        clear_existing = options['clear_existing']

        # Validate file existence
        if not os.path.exists(mapping_file):
            raise CommandError(f'Mapping matrix file not found: {mapping_file}')

        if not os.path.exists(unified_file):
            raise CommandError(f'Unified referentiel file not found: {unified_file}')

        self.stdout.write(f'Processing files:')
        self.stdout.write(f'  - Mapping Matrix: {mapping_file}')
        self.stdout.write(f'  - Unified Referentiel: {unified_file}')

        try:
            with transaction.atomic():
                if clear_existing:
                    self.clear_existing_data()

                # Process unified referentiel first (creates unified framework)
                self.process_unified_referentiel(unified_file)

                # Then process mapping matrix (creates individual frameworks)
                self.process_mapping_matrix(mapping_file)

                self.stdout.write(
                    self.style.SUCCESS('Successfully imported Excel data!')
                )

        except Exception as e:
            raise CommandError(f'Error processing files: {str(e)}')

    def clear_existing_data(self):
        """Clear existing framework data"""
        self.stdout.write('Clearing existing data...')
        Control.objects.all().delete()
        ControlCategory.objects.all().delete()
        Framework.objects.all().delete()
        self.stdout.write('Existing data cleared.')

    def process_unified_referentiel(self, file_path):
        """Process the unified referentiel Excel file"""
        self.stdout.write('Processing unified referentiel file...')

        # Read Excel file
        df = pd.read_excel(file_path)

        # Expected columns: domain id, domain name, control id, unified control description,
        # iso27001(22), iec 62443, nis2.0
        expected_columns = [
            'domain id', 'domain name', 'control id',
            'unified control description', 'iso27001(22)',
            'iec 62443', 'nis2.0'
        ]

        # Check if columns exist (case-insensitive)
        df.columns = [col.lower().strip() for col in df.columns]

        # Create or get the Unified Framework
        unified_framework, created = Framework.objects.get_or_create(
            name='Unified Framework',
            defaults={
                'description': 'Unified compliance framework combining ISO 27001, IEC 62443, and NIS2',
                'version': '1.0'
            }
        )

        if created:
            self.stdout.write('Created Unified Framework')
        else:
            self.stdout.write('Using existing Unified Framework')

        # Process domains and controls
        domains_created = set()
        controls_created = 0

        for index, row in df.iterrows():
            try:
                domain_id = str(row.get('domain id', '')).strip()
                domain_name = str(row.get('domain name', '')).strip()
                control_id = str(row.get('control id', '')).strip()
                description = str(row.get('unified control description', '')).strip()

                # Skip empty rows
                if not all([domain_id, domain_name, control_id, description]):
                    continue

                # Create or get domain (category)
                if domain_id not in domains_created:
                    category, cat_created = ControlCategory.objects.get_or_create(
                        framework=unified_framework,
                        code=domain_id,
                        defaults={
                            'name': domain_name,
                            'description': f'Domain: {domain_name}'
                        }
                    )
                    if cat_created:
                        domains_created.add(domain_id)
                        self.stdout.write(f'  Created domain: {domain_name}')
                else:
                    category = ControlCategory.objects.get(
                        framework=unified_framework,
                        code=domain_id
                    )

                # Create control
                control, ctrl_created = Control.objects.get_or_create(
                    framework=unified_framework,
                    control_id=control_id,
                    defaults={
                        'category': category,
                        'title': f'Unified Control {control_id}',
                        'description': description,
                        'implementation_guidance': self.build_implementation_guidance(row)
                    }
                )

                if ctrl_created:
                    controls_created += 1

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error processing row {index + 1}: {str(e)}')
                )
                continue

        self.stdout.write(f'Created {len(domains_created)} domains and {controls_created} controls for Unified Framework')

    def process_mapping_matrix(self, file_path):
        """Process the mapping matrix Excel file"""
        self.stdout.write('Processing mapping matrix file...')

        # Read Excel file
        df = pd.read_excel(file_path)

        # Expected columns: domain, control, description, iso27001(22), iec 62443, nis2.0
        df.columns = [col.lower().strip() for col in df.columns]

        # Create individual frameworks
        frameworks_info = {
            'iso27001(22)': {
                'name': 'ISO/IEC 27001:2022',
                'description': 'Information security management systems - Requirements',
                'version': '2022'
            },
            'iec 62443': {
                'name': 'IEC 62443',
                'description': 'Industrial communication networks - Network and system security',
                'version': '2018'
            },
            'nis2.0': {
                'name': 'NIS2 Directive',
                'description': 'Network and Information Security Directive',
                'version': '2.0'
            }
        }

        created_frameworks = {}

        # Create frameworks
        for col_name, info in frameworks_info.items():
            framework, created = Framework.objects.get_or_create(
                name=info['name'],
                defaults={
                    'description': info['description'],
                    'version': info['version']
                }
            )
            created_frameworks[col_name] = framework
            if created:
                self.stdout.write(f'Created framework: {info["name"]}')

        # Process controls for each framework
        for framework_col, framework_obj in created_frameworks.items():
            self.process_framework_controls(df, framework_obj, framework_col)

    def process_framework_controls(self, df, framework, framework_column):
        """Process controls for a specific framework"""
        self.stdout.write(f'Processing controls for {framework.name}...')

        domains_created = set()
        controls_created = 0

        for index, row in df.iterrows():
            try:
                domain = str(row.get('domain', '')).strip()
                control_ref = str(row.get('control', '')).strip()
                description = str(row.get('description', '')).strip()
                framework_control = str(row.get(framework_column, '')).strip()

                # Skip if no mapping exists for this framework
                if not framework_control or framework_control.lower() in ['nan', 'n/a', '']:
                    continue

                # Skip empty rows
                if not all([domain, control_ref, description]):
                    continue

                # Create or get domain (category)
                domain_code = domain.replace(' ', '_').upper()
                if domain_code not in domains_created:
                    category, cat_created = ControlCategory.objects.get_or_create(
                        framework=framework,
                        code=domain_code,
                        defaults={
                            'name': domain,
                            'description': f'Domain: {domain}'
                        }
                    )
                    if cat_created:
                        domains_created.add(domain_code)
                else:
                    category = ControlCategory.objects.get(
                        framework=framework,
                        code=domain_code
                    )

                # Create control
                control, ctrl_created = Control.objects.get_or_create(
                    framework=framework,
                    control_id=framework_control,
                    defaults={
                        'category': category,
                        'title': control_ref,
                        'description': description,
                        'implementation_guidance': f'Reference: {control_ref}'
                    }
                )

                if ctrl_created:
                    controls_created += 1

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error processing row {index + 1} for {framework.name}: {str(e)}')
                )
                continue

        self.stdout.write(f'Created {controls_created} controls for {framework.name}')

    def build_implementation_guidance(self, row):
        """Build implementation guidance from framework mappings"""
        guidance = []

        iso_ref = str(row.get('iso27001(22)', '')).strip()
        iec_ref = str(row.get('iec 62443', '')).strip()
        nis_ref = str(row.get('nis2.0', '')).strip()

        if iso_ref and iso_ref.lower() not in ['nan', 'n/a']:
            guidance.append(f"ISO 27001: {iso_ref}")

        if iec_ref and iec_ref.lower() not in ['nan', 'n/a']:
            guidance.append(f"IEC 62443: {iec_ref}")

        if nis_ref and nis_ref.lower() not in ['nan', 'n/a']:
            guidance.append(f"NIS2: {nis_ref}")

        return '\n'.join(guidance) if guidance else 'No specific framework mappings available'
