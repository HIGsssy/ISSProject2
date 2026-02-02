"""
CSV Import Utility for Child Records

Handles CSV parsing, validation, and bulk import of child records with encryption support.
"""
import csv
import io
from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from core.models import Child, Centre


class CSVImportError(Exception):
    """Custom exception for CSV import errors."""
    pass


class ChildCSVImporter:
    """
    Handles CSV import of child records with validation and encryption.
    
    Required fields:
    - first_name
    - last_name
    - date_of_birth (YYYY-MM-DD)
    
    Optional fields:
    - address_line1, address_line2, city, province, postal_code
    - alternate_location
    - guardian1_name, guardian1_home_phone, guardian1_work_phone, guardian1_cell_phone, guardian1_email
    - guardian2_name, guardian2_home_phone, guardian2_work_phone, guardian2_cell_phone, guardian2_email
    - centre (centre name)
    - start_date (YYYY-MM-DD, defaults to today)
    - end_date (YYYY-MM-DD, for discharged children)
    - discharge_reason (for discharged children)
    - notes
    - on_hold (true/false, defaults to false)
    - referral_source_type (parent_guardian/other_agency)
    - referral_source_name, referral_source_phone
    - referral_agency_name, referral_agency_address
    - referral_reason_cognitive, referral_reason_language, referral_reason_gross_motor,
      referral_reason_fine_motor, referral_reason_social_emotional, referral_reason_self_help,
      referral_reason_other (all true/false)
    - referral_reason_details
    - attends_childcare (true/false), childcare_centre (centre name), childcare_frequency
    - attends_earlyon (true/false), earlyon_centre (centre name), earlyon_frequency
    - agency_continuing_involvement (true/false)
    - referral_consent_on_file (true/false)
    
    Note: All imported children default to 'active' overall_status and
    'awaiting_assignment' caseload_status. Discharge should be done through
    the discharge workflow, not via import.
    """
    
    REQUIRED_FIELDS = ['first_name', 'last_name', 'date_of_birth']
    OPTIONAL_FIELDS = [
        'address_line1', 'address_line2', 'city', 'province', 'postal_code',
        'alternate_location',
        'guardian1_name', 'guardian1_home_phone', 'guardian1_work_phone', 'guardian1_cell_phone', 'guardian1_email',
        'guardian2_name', 'guardian2_home_phone', 'guardian2_work_phone', 'guardian2_cell_phone', 'guardian2_email',
        'centre', 'start_date', 'end_date', 'discharge_reason', 'notes', 'on_hold',
        'referral_source_type', 'referral_source_name', 'referral_source_phone',
        'referral_agency_name', 'referral_agency_address',
        'referral_reason_cognitive', 'referral_reason_language', 'referral_reason_gross_motor',
        'referral_reason_fine_motor', 'referral_reason_social_emotional', 'referral_reason_self_help',
        'referral_reason_other', 'referral_reason_details',
        'attends_childcare', 'childcare_centre', 'childcare_frequency',
        'attends_earlyon', 'earlyon_centre', 'earlyon_frequency',
        'agency_continuing_involvement', 'referral_consent_on_file'
    ]
    
    def __init__(self, csv_file, user):
        """
        Initialize importer.
        
        Args:
            csv_file: Uploaded CSV file object
            user: User performing the import (for audit trail)
        """
        self.csv_file = csv_file
        self.user = user
        self.rows = []
        self.valid_rows = []
        self.invalid_rows = []
        self.centres_cache = {}
        
    def parse(self):
        """
        Parse CSV file and validate rows.
        
        Returns:
            dict: {'valid': list, 'invalid': list, 'total': int}
        """
        try:
            # Read file content
            content = self.csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Get headers
            headers = csv_reader.fieldnames
            if not headers:
                raise CSVImportError("CSV file is empty or invalid")
            
            # Check required fields
            missing_fields = [field for field in self.REQUIRED_FIELDS if field not in headers]
            if missing_fields:
                raise CSVImportError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Process each row
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (account for header)
                result = self._validate_row(row, row_num)
                if result['valid']:
                    self.valid_rows.append(result)
                else:
                    self.invalid_rows.append(result)
            
            return {
                'valid': self.valid_rows,
                'invalid': self.invalid_rows,
                'total': len(self.valid_rows) + len(self.invalid_rows)
            }
            
        except UnicodeDecodeError:
            raise CSVImportError("Invalid file encoding. Please use UTF-8 encoded CSV.")
        except csv.Error as e:
            raise CSVImportError(f"CSV parsing error: {str(e)}")
    
    def _validate_row(self, row, row_num):
        """
        Validate a single CSV row.
        
        Args:
            row: Dictionary of CSV row data
            row_num: Row number (for error reporting)
            
        Returns:
            dict: {'valid': bool, 'data': dict, 'errors': list, 'row_num': int}
        """
        errors = []
        data = {}
        
        # Strip whitespace from all values
        row = {k: v.strip() if v else '' for k, v in row.items()}
        
        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            value = row.get(field, '').strip()
            if not value:
                errors.append(f"{field} is required")
            else:
                data[field] = value
        
        # If required fields are missing, return early
        if errors:
            return {
                'valid': False,
                'data': row,
                'raw_data': row,
                'errors': errors,
                'row_num': row_num
            }
        
        # Validate date_of_birth
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            data['date_of_birth'] = dob
            
            # Check if date is reasonable (not in future, not too old)
            today = datetime.now().date()
            if dob > today:
                errors.append("date_of_birth cannot be in the future")
            elif (today.year - dob.year) > 25:
                errors.append("date_of_birth seems too old (>25 years)")
        except ValueError:
            errors.append("date_of_birth must be in YYYY-MM-DD format")
        
        # Parse boolean fields
        boolean_fields = [
            'on_hold', 'referral_reason_cognitive', 'referral_reason_language',
            'referral_reason_gross_motor', 'referral_reason_fine_motor',
            'referral_reason_social_emotional', 'referral_reason_self_help',
            'referral_reason_other', 'attends_childcare', 'attends_earlyon',
            'agency_continuing_involvement', 'referral_consent_on_file'
        ]
        for field in boolean_fields:
            value = row.get(field, '').strip().lower()
            if value in ['true', '1', 'yes', 'y']:
                data[field] = True
            elif value in ['false', '0', 'no', 'n', '']:
                data[field] = False if value else False
            else:
                errors.append(f"{field} must be true/false/yes/no/1/0")
        
        # Validate centre if provided
        centre_name = row.get('centre', '').strip()
        if centre_name:
            centre = self._lookup_centre(centre_name)
            if centre:
                data['centre'] = centre
            else:
                errors.append(f"Centre '{centre_name}' not found")
        
        # Validate childcare_centre if provided
        childcare_centre_name = row.get('childcare_centre', '').strip()
        if childcare_centre_name:
            childcare_centre = self._lookup_centre(childcare_centre_name)
            if childcare_centre:
                data['childcare_centre'] = childcare_centre
            else:
                errors.append(f"Childcare centre '{childcare_centre_name}' not found")
        
        # Validate earlyon_centre if provided
        earlyon_centre_name = row.get('earlyon_centre', '').strip()
        if earlyon_centre_name:
            earlyon_centre = self._lookup_centre(earlyon_centre_name)
            if earlyon_centre:
                data['earlyon_centre'] = earlyon_centre
            else:
                errors.append(f"EarlyON centre '{earlyon_centre_name}' not found")
        
        # Validate start_date if provided
        start_date = row.get('start_date', '').strip()
        if start_date:
            try:
                data['start_date'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("start_date must be in YYYY-MM-DD format")
        
        # Validate end_date if provided
        end_date = row.get('end_date', '').strip()
        if end_date:
            try:
                data['end_date'] = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("end_date must be in YYYY-MM-DD format")
        
        # Validate referral_source_type if provided
        ref_type = row.get('referral_source_type', '').strip().lower()
        if ref_type:
            if ref_type in ['parent_guardian', 'other_agency']:
                data['referral_source_type'] = ref_type
            else:
                errors.append("referral_source_type must be 'parent_guardian' or 'other_agency'")
        
        # Validate email fields if provided
        for email_field in ['guardian1_email', 'guardian2_email']:
            email = row.get(email_field, '').strip()
            if email:
                try:
                    validate_email(email)
                    data[email_field] = email
                except ValidationError:
                    errors.append(f"{email_field} is not a valid email address")
        
        # Copy optional text fields
        text_fields = [
            'address_line1', 'address_line2', 'city', 'province', 'postal_code',
            'alternate_location',
            'guardian1_name', 'guardian1_home_phone', 'guardian1_work_phone', 'guardian1_cell_phone',
            'guardian2_name', 'guardian2_home_phone', 'guardian2_work_phone', 'guardian2_cell_phone',
            'discharge_reason', 'notes',
            'referral_source_name', 'referral_source_phone',
            'referral_agency_name', 'referral_agency_address',
            'referral_reason_details',
            'childcare_frequency', 'earlyon_frequency'
        ]
        for field in text_fields:
            value = row.get(field, '').strip()
            if value:
                data[field] = value
        
        return {
            'valid': len(errors) == 0,
            'data': data,
            'raw_data': row,
            'errors': errors,
            'row_num': row_num
        }
    
    def _lookup_centre(self, centre_name):
        """
        Lookup centre by name with caching.
        
        Args:
            centre_name: Centre name to lookup
            
        Returns:
            Centre object or None
        """
        if centre_name not in self.centres_cache:
            try:
                centre = Centre.objects.get(name__iexact=centre_name, status='active')
                self.centres_cache[centre_name] = centre
            except Centre.DoesNotExist:
                self.centres_cache[centre_name] = None
            except Centre.MultipleObjectsReturned:
                # If multiple centres with same name, use first active one
                centre = Centre.objects.filter(name__iexact=centre_name, status='active').first()
                self.centres_cache[centre_name] = centre
        
        return self.centres_cache[centre_name]
    
    def check_duplicates(self):
        """
        Check for potential duplicates in valid rows based on name and DOB.
        
        Returns:
            list: List of potential duplicates with details
        """
        duplicates = []
        
        for row in self.valid_rows:
            data = row['data']
            # Check if child already exists with same name and DOB
            existing = Child.objects.filter(
                first_name=data['first_name'],
                last_name=data['last_name'],
                date_of_birth=data['date_of_birth']
            ).first()
            
            if existing:
                duplicates.append({
                    'row_num': row['row_num'],
                    'name': f"{data['first_name']} {data['last_name']}",
                    'dob': data['date_of_birth'],
                    'existing_id': existing.id
                })
        
        return duplicates
    
    def import_records(self, skip_duplicates=True):
        """
        Import valid records into database.
        
        Args:
            skip_duplicates: If True, skip rows that would create duplicates
            
        Returns:
            dict: {'created': int, 'skipped': int, 'errors': list}
        """
        created_count = 0
        skipped_count = 0
        errors = []
        
        for row in self.valid_rows:
            try:
                data = row['data'].copy()
                
                # Check for duplicate if skip_duplicates is True
                if skip_duplicates:
                    existing = Child.objects.filter(
                        first_name=data['first_name'],
                        last_name=data['last_name'],
                        date_of_birth=data['date_of_birth']
                    ).exists()
                    
                    if existing:
                        skipped_count += 1
                        continue
                
                # Create child record - all imports default to active/awaiting_assignment
                child = Child(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    date_of_birth=data['date_of_birth'],
                    overall_status='active',
                    caseload_status='awaiting_assignment',
                    on_hold=data.get('on_hold', False),
                    created_by=self.user,
                    updated_by=self.user
                )
                
                # Set optional FK fields
                if 'centre' in data:
                    child.centre = data['centre']
                if 'childcare_centre' in data:
                    child.childcare_centre = data['childcare_centre']
                if 'earlyon_centre' in data:
                    child.earlyon_centre = data['earlyon_centre']
                    
                # Set date fields
                if 'start_date' in data:
                    child.start_date = data['start_date']
                if 'end_date' in data:
                    child.end_date = data['end_date']
                
                # Set address fields
                for field in ['address_line1', 'address_line2', 'city', 'province', 'postal_code', 'alternate_location']:
                    if field in data:
                        setattr(child, field, data[field])
                
                # Set guardian 1 fields
                for field in ['guardian1_name', 'guardian1_home_phone', 'guardian1_work_phone', 
                              'guardian1_cell_phone', 'guardian1_email']:
                    if field in data:
                        setattr(child, field, data[field])
                
                # Set guardian 2 fields
                for field in ['guardian2_name', 'guardian2_home_phone', 'guardian2_work_phone',
                              'guardian2_cell_phone', 'guardian2_email']:
                    if field in data:
                        setattr(child, field, data[field])
                
                # Set referral fields
                referral_fields = [
                    'referral_source_type', 'referral_source_name', 'referral_source_phone',
                    'referral_agency_name', 'referral_agency_address',
                    'referral_reason_cognitive', 'referral_reason_language',
                    'referral_reason_gross_motor', 'referral_reason_fine_motor',
                    'referral_reason_social_emotional', 'referral_reason_self_help',
                    'referral_reason_other', 'referral_reason_details',
                    'agency_continuing_involvement', 'referral_consent_on_file'
                ]
                for field in referral_fields:
                    if field in data:
                        setattr(child, field, data[field])
                
                # Set program attendance fields
                for field in ['attends_childcare', 'childcare_frequency', 
                              'attends_earlyon', 'earlyon_frequency']:
                    if field in data:
                        setattr(child, field, data[field])
                
                # Set other fields
                for field in ['discharge_reason', 'notes']:
                    if field in data:
                        setattr(child, field, data[field])
                
                child.save()
                created_count += 1
                
            except Exception as e:
                errors.append({
                    'row_num': row['row_num'],
                    'error': str(e)
                })
        
        return {
            'created': created_count,
            'skipped': skipped_count,
            'errors': errors
        }
    
    @staticmethod
    def generate_template():
        """
        Generate a CSV template with headers and example data.
        
        Returns:
            str: CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers - split into logical groups for readability
        headers = [
            # Required
            'first_name', 'last_name', 'date_of_birth',
            # Centre assignment
            'centre', 'start_date', 'on_hold',
            # Address
            'address_line1', 'address_line2', 'city', 'province', 'postal_code', 'alternate_location',
            # Guardian 1
            'guardian1_name', 'guardian1_home_phone', 'guardian1_work_phone', 'guardian1_cell_phone', 'guardian1_email',
            # Guardian 2
            'guardian2_name', 'guardian2_home_phone', 'guardian2_work_phone', 'guardian2_cell_phone', 'guardian2_email',
            # Referral source
            'referral_source_type', 'referral_source_name', 'referral_source_phone',
            'referral_agency_name', 'referral_agency_address',
            # Referral reasons (true/false)
            'referral_reason_cognitive', 'referral_reason_language', 'referral_reason_gross_motor',
            'referral_reason_fine_motor', 'referral_reason_social_emotional', 'referral_reason_self_help',
            'referral_reason_other', 'referral_reason_details',
            # Program attendance
            'attends_childcare', 'childcare_centre', 'childcare_frequency',
            'attends_earlyon', 'earlyon_centre', 'earlyon_frequency',
            # Referral details
            'agency_continuing_involvement', 'referral_consent_on_file',
            # Other
            'notes'
        ]
        writer.writerow(headers)
        
        # Write example row 1 - minimal data (required fields only)
        example1 = [
            'John', 'Smith', '2015-03-15',  # Required
            '', '', 'false',  # Centre assignment
            '', '', '', '', '', '',  # Address
            '', '', '', '', '',  # Guardian 1
            '', '', '', '', '',  # Guardian 2
            '', '', '',  # Referral source
            '', '',  # Referral agency
            'false', 'false', 'false', 'false', 'false', 'false', 'false', '',  # Referral reasons
            'false', '', '',  # Childcare
            'false', '', '',  # EarlyON
            'false', 'false',  # Referral details
            ''  # Notes
        ]
        writer.writerow(example1)
        
        # Write example row 2 - parent/guardian referral with basic info
        example2 = [
            'Jane', 'Doe', '2016-07-22',  # Required
            'Main Centre', '2024-01-01', 'false',  # Centre assignment
            '456 Oak Ave', 'Unit 10', 'Toronto', 'ON', 'M1A 1A1', '',  # Address
            'John Doe', '416-555-0100', '416-555-0101', '647-555-0102', 'john@example.com',  # Guardian 1
            'Mary Doe', '', '416-555-0200', '647-555-0201', 'mary@example.com',  # Guardian 2
            'parent_guardian', 'John Doe', '647-555-0102',  # Referral source
            '', '',  # Referral agency
            'true', 'true', 'false', 'false', 'false', 'false', 'false', 'Concerns with speech development',  # Referral reasons
            'true', 'ABC Childcare', 'Full-time',  # Childcare
            'false', '', '',  # EarlyON
            'false', 'true',  # Referral details
            'Parent referred'  # Notes
        ]
        writer.writerow(example2)
        
        # Write example row 3 - agency referral with full details
        example3 = [
            'Tim', 'Wilson', '2014-11-30',  # Required
            '', '2023-06-01', 'false',  # Centre assignment
            '789 Pine Street', '', 'Mississauga', 'ON', 'L5A 2B3', 'Lives with grandmother at same address',  # Address
            'Lisa Wilson', '905-555-0300', '', '905-555-0301', 'lisa@example.com',  # Guardian 1
            '', '', '', '', '',  # Guardian 2
            'other_agency', 'Dr. Sarah Johnson', '416-555-4000',  # Referral source
            'Community Health Services', '100 Medical Drive, Toronto ON',  # Referral agency
            'false', 'false', 'true', 'true', 'true', 'false', 'false', 'Motor skills and social/emotional development concerns',  # Referral reasons
            'false', '', '',  # Childcare
            'true', 'Downtown EarlyON', 'Weekly',  # EarlyON
            'true', 'true',  # Referral details
            'Agency continuing follow-up'  # Notes
        ]
        writer.writerow(example3)
        
        return output.getvalue()
