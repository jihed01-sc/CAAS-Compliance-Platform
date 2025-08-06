# management/commands/import_frameworks.py
import pandas as pd
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from compliance.models import Framework, ControlCategory, Control, ControlMapping


class Command(BaseCommand):
    help = 'Import compliance frameworks from CSV or Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the CSV or Excel file to import'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            help='Excel sheet name to import (optional, imports all sheets if not specified)',
            default=None
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before import',
            default=False
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        sheet_name = options['sheet']
        clear_data = options['clear']

        self.stdout.write(f"Starting import from: {file_path}")

        # Check if file exists
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        # Get file extension
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.csv':
                # Read CSV file
                df = pd.read_csv(file_path)
                self.stdout.write(f"Successfully loaded {len(df)} rows from CSV")
                self.process_dataframe(df, clear_data)

            elif file_ext in ['.xlsx', '.xls']:
                # Read Excel file
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    self.stdout.write(f"Reading sheet: {sheet_name}")
                    self.process_dataframe(df, clear_data)
                else:
                    # Read all sheets
                    excel_file = pd.ExcelFile(file_path)
                    self.stdout.write(f"Found sheets: {excel_file.sheet_names}")

                    # Process each sheet
                    for i, sheet in enumerate(excel_file.sheet_names):
                        self.stdout.write(f"Processing sheet: {sheet}")
                        df = pd.read_excel(file_path, sheet_name=sheet)
                        # Only clear data for the first sheet
                        self.process_dataframe(df, clear_data and i == 0)
            else:
                raise CommandError(f"Unsupported file format: {file_ext}. Supported formats: .csv, .xlsx, .xls")

        except Exception as e:
            raise CommandError(f"Error reading file: {str(e)}")

    def process_dataframe(self, df, clear_data=False):
        """Process a single dataframe"""

        # Check required columns
        required_columns = ['Framework', 'Control ID', 'Title', 'Category', 'Description']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise CommandError(f"Missing required columns: {missing_columns}")

        # Clean the data
        df = df.dropna(subset=['Framework', 'Control ID', 'Title'])
        df = df.fillna('')

        self.stdout.write(f"Processing {len(df)} records...")

        with transaction.atomic():
            # Clear existing data
            if clear_data:
                self.stdout.write("Clearing existing data...")
                Control.objects.all().delete()
                ControlCategory.objects.all().delete()
                Framework.objects.all().delete()

            # Track statistics
            frameworks_created = 0
            categories_created = 0
            controls_created = 0
            controls_updated = 0

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Get or create framework
                    framework, created = Framework.objects.get_or_create(
                        name=row['Framework'],
                        defaults={'description': f"{row['Framework']} compliance framework"}
                    )
                    if created:
                        frameworks_created += 1
                        self.stdout.write(f"Created framework: {framework.name}")

                    # Get or create category with better unique code generation
                    category_name = row['Category']
                    category_code = self.generate_unique_category_code(category_name, framework)

                    category, created = ControlCategory.objects.get_or_create(
                        name=category_name,
                        framework=framework,
                        defaults={
                            'code': category_code,
                            'description': f"{category_name} category for {framework.name}"
                        }
                    )
                    if created:
                        categories_created += 1

                    # Get or create control
                    control, created = Control.objects.get_or_create(
                        framework=framework,
                        control_id=row['Control ID'],
                        defaults={
                            'title': row['Title'],
                            'category': category,
                            'description': row['Description'],
                            'recommendation': row.get('Recommendation', ''),
                        }
                    )

                    if created:
                        controls_created += 1
                    else:
                        # Update existing control
                        control.title = row['Title']
                        control.category = category
                        control.description = row['Description']
                        control.recommendation = row.get('Recommendation', '')
                        control.save()
                        controls_updated += 1

                    if (index + 1) % 50 == 0:
                        self.stdout.write(f"Processed {index + 1} records...")

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing row {index + 1}: {str(e)}")
                    )
                    continue

            # Print summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nImport completed successfully!\n"
                    f"Frameworks created: {frameworks_created}\n"
                    f"Categories created: {categories_created}\n"
                    f"Controls created: {controls_created}\n"
                    f"Controls updated: {controls_updated}\n"
                    f"Total records processed: {len(df)}"
                )
            )

    def generate_unique_category_code(self, category_name, framework):
        """Generate a unique category code for the given framework"""
        base_code = category_name[:10].replace(' ', '_').upper()

        # Check if this code already exists for this framework
        counter = 1
        code = base_code

        while ControlCategory.objects.filter(framework=framework, code=code).exists():
            code = f"{base_code}_{counter}"
            counter += 1

        return code

    def create_mappings(self):
        """Create mappings between controls if mapping data exists"""
        # This is a placeholder for control mapping logic
        # You would implement this based on your mapping data structure
        pass