#!/usr/bin/env python
"""
Simple Excel Data Import Script for CAAS Compliance Framework
This script processes your Excel files and imports them into the Django database.
"""

import os
import sys
import pandas as pd

# Add the project path to Django settings
sys.path.append('C:/Users/Jihed/PycharmProjects/CAAS_App')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')

import django
django.setup()

from compliance.models import Framework, ControlCategory, Control
from django.db import transaction


def clear_existing_data():
    """Clear existing framework data"""
    print("Clearing existing data...")
    Control.objects.all().delete()
    ControlCategory.objects.all().delete()
    Framework.objects.all().delete()
    print("Existing data cleared.")


def process_unified_referentiel(file_path):
    """Process the unified referentiel Excel file"""
    print(f"Processing unified referentiel file: {file_path}")

    # Read Excel file
    df = pd.read_excel(file_path)

    # Normalize column names (case-insensitive)
    df.columns = [col.lower().strip() for col in df.columns]

    # Print actual column names for debugging
    print("Actual columns in unified referentiel:", list(df.columns))

    # Create or get the Unified Framework
    unified_framework, created = Framework.objects.get_or_create(
        name='Unified Framework',
        defaults={
            'description': 'Unified compliance framework combining ISO 27001, IEC 62443, and NIS2',
            'version': '1.0'
        }
    )

    if created:
        print("Created Unified Framework")
    else:
        print("Using existing Unified Framework")

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
                    print(f"  Created domain: {domain_name}")
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
                    'implementation_guidance': build_implementation_guidance(row)
                }
            )

            if ctrl_created:
                controls_created += 1

        except Exception as e:
            print(f"Error processing row {index + 1}: {str(e)}")
            continue

    print(f"Created {len(domains_created)} domains and {controls_created} controls for Unified Framework")


def process_mapping_matrix(file_path):
    """Process the mapping matrix Excel file"""
    print(f"Processing mapping matrix file: {file_path}")

    # Read Excel file
    df = pd.read_excel(file_path)

    # Normalize column names
    df.columns = [col.lower().strip() for col in df.columns]

    # Print actual column names for debugging
    print("Actual columns in mapping matrix:", list(df.columns))
    print(f"Total rows in mapping matrix: {len(df)}")
    print()

    # Create individual frameworks with updated column mappings
    frameworks_info = {
        'iso 27001 (2022)': {
            'name': 'ISO/IEC 27001:2022',
            'description': 'Information security management systems - Requirements',
            'version': '2022'
        },
        'iec 62443': {
            'name': 'IEC 62443',
            'description': 'Industrial communication networks - Network and system security',
            'version': '2018'
        },
        'nis2 directive': {
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
            print(f"Created framework: {info['name']}")

    # Process controls for each framework
    for framework_col, framework_obj in created_frameworks.items():
        process_framework_controls(df, framework_obj, framework_col)


def extract_main_control_id(control_text):
    """Extract the main control ID from long control text"""
    if not control_text or str(control_text).lower() in ['nan', 'n/a', '', 'none']:
        return ''

    control_text = str(control_text).strip()

    # Split by common separators and take the first meaningful part
    # Handle cases like "A.8 Asset Management" or "ISA 62443-2-1:2009 4.2.3.4"
    lines = control_text.split('\n')
    first_line = lines[0].strip()

    # For ISO controls, extract pattern like "A.8" or "5.14"
    if 'A.' in first_line or any(char.isdigit() for char in first_line[:10]):
        # Take first part before any description
        parts = first_line.split(' ')
        if len(parts) > 0:
            main_id = parts[0]
            # Add second part if it looks like part of the ID
            if len(parts) > 1 and (parts[1].replace('.', '').isdigit() or len(parts[1]) < 20):
                main_id += ' ' + parts[1]
            return main_id[:200]  # Limit to 50 chars

    # For IEC controls, extract pattern like "ISA 62443-2-1:2009 4.2.3.4"
    if 'ISA' in first_line or 'IEC' in first_line or '62443' in first_line:
        # Find the main standard reference
        parts = first_line.split(' ')
        if len(parts) >= 2:
            # Take first two parts like "ISA 62443-2-1:2009"
            main_id = ' '.join(parts[:2])
            return main_id[:200]  # Limit to 50 chars

    # For NIS2 controls, extract pattern like "Art.3.2" or "Art. 21(2)(c)"
    if 'Art' in first_line:
        # Extract just the article reference
        import re
        match = re.search(r'Art\.?\s*\d+[^\s,]*(?:\([^)]+\))*', first_line)
        if match:
            return match.group(0)[:50]

    # Fallback: take first 50 characters
    return first_line[:200]

def process_framework_controls(df, framework, framework_column):
    """Process controls for a specific framework"""
    print(f"Processing controls for {framework.name}...")
    print(f"Looking for column: '{framework_column}'")

    domains_created = set()
    controls_created = 0
    skipped_empty = 0
    skipped_no_mapping = 0
    errors = 0
    truncated_ids = 0

    for index, row in df.iterrows():
        try:
            domain = str(row.get('domain', '')).strip()
            control_ref = str(row.get('control', '')).strip()
            description = str(row.get('description', '')).strip()
            framework_control_raw = str(row.get(framework_column, '')).strip()

            # Extract main control ID instead of using full text
            framework_control = extract_main_control_id(framework_control_raw)

            # Debug: Print first few rows to see what's happening
            if index < 5:
                print(f"  Row {index + 1}: domain='{domain}', control='{control_ref}'")
                print(f"    Raw ID: '{framework_control_raw[:100]}...' -> Extracted: '{framework_control}'")

            # Skip if no mapping exists for this framework
            if not framework_control:
                skipped_no_mapping += 1
                continue

            # Track if we truncated the ID
            if len(framework_control_raw) > len(framework_control):
                truncated_ids += 1

            # Skip empty rows
            if not all([domain, control_ref, description]):
                skipped_empty += 1
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
                    print(f"    Created domain: {domain}")
            else:
                category = ControlCategory.objects.get(
                    framework=framework,
                    code=domain_code
                )

            # Create control with extracted ID but store full reference in implementation guidance
            control, ctrl_created = Control.objects.get_or_create(
                framework=framework,
                control_id=framework_control,
                defaults={
                    'category': category,
                    'title': control_ref,
                    'description': description,
                    'implementation_guidance': f'Reference: {control_ref}\nFull Control ID: {framework_control_raw}'
                }
            )

            if ctrl_created:
                controls_created += 1
            else:
                print(f"    Control already exists: {framework_control}")

        except Exception as e:
            errors += 1
            print(f"Error processing row {index + 1} for {framework.name}: {str(e)}")
            continue

    print(f"Statistics for {framework.name}:")
    print(f"  - Total rows processed: {len(df)}")
    print(f"  - Controls created: {controls_created}")
    print(f"  - Skipped (no mapping): {skipped_no_mapping}")
    print(f"  - Skipped (empty data): {skipped_empty}")
    print(f"  - Errors: {errors}")
    print(f"  - Truncated long IDs: {truncated_ids}")
    print(f"  - Domains created: {len(domains_created)}")
    print()


def build_implementation_guidance(row):
    """Build implementation guidance from framework mappings"""
    guidance = []

    # Updated column names to match your Excel files
    iso_ref = str(row.get('iso 27001:2022', '')).strip()
    iec_ref = str(row.get('iec 62443 reference', '')).strip()
    nis_ref = str(row.get('nis2 directive', '')).strip()

    if iso_ref and iso_ref.lower() not in ['nan', 'n/a', '']:
        guidance.append(f"ISO 27001: {iso_ref}")

    if iec_ref and iec_ref.lower() not in ['nan', 'n/a', '']:
        guidance.append(f"IEC 62443: {iec_ref}")

    if nis_ref and nis_ref.lower() not in ['nan', 'n/a', '']:
        guidance.append(f"NIS2: {nis_ref}")

    return '\n'.join(guidance) if guidance else 'No specific framework mappings available'


def main():
    """Main function to run the import process"""
    print("=== CAAS Excel Data Import Tool ===")
    print()

    # Get file paths from user input
    print("Please provide the full paths to your Excel files:")

    mapping_file = input("Mapping Matrix file path: ").strip().strip('"')
    unified_file = input("Unified Referentiel file path: ").strip().strip('"')

    # Validate file existence
    if not os.path.exists(mapping_file):
        print(f"ERROR: Mapping matrix file not found: {mapping_file}")
        return

    if not os.path.exists(unified_file):
        print(f"ERROR: Unified referentiel file not found: {unified_file}")
        return

    # Ask about clearing existing data
    clear_data = input("Clear existing framework data? (yes/no): ").lower().strip()

    print()
    print("Starting import process...")
    print(f"Mapping Matrix: {mapping_file}")
    print(f"Unified Referentiel: {unified_file}")
    print()

    try:
        with transaction.atomic():
            if clear_data in ['yes', 'y']:
                clear_existing_data()

            # Process unified referentiel first (creates unified framework)
            process_unified_referentiel(unified_file)

            # Then process mapping matrix (creates individual frameworks)
            process_mapping_matrix(mapping_file)

            print()
            print("✅ Successfully imported Excel data!")
            print()
            print("Created frameworks:")
            for framework in Framework.objects.all():
                controls_count = Control.objects.filter(framework=framework).count()
                print(f"  - {framework.name}: {controls_count} controls")

    except Exception as e:
        print(f"❌ Error processing files: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
