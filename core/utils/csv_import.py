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
    - status (active, on_hold, discharged, non_caseload)
    
    Optional fields:
    - address_line1, address_line2, city, province, postal_code
    - guardian1_name, guardian1_phone, guardian1_email
    - guardian2_name, guardian2_phone, guardian2_email
    - centre (centre name)
    - start_date (YYYY-MM-DD, defaults to today)
    - end_date (YYYY-MM-DD, required if status=discharged)
    - discharge_reason (required if status=discharged)
    - notes
    """
    
    REQUIRED_FIELDS = ['first_name', 'last_name', 'date_of_birth', 'status']
    OPTIONAL_FIELDS = [
        'address_line1', 'address_line2', 'city', 'province', 'postal_code',
        'guardian1_name', 'guardian1_phone', 'guardian1_email',
        'guardian2_name', 'guardian2_phone', 'guardian2_email',
        'centre', 'start_date', 'end_date', 'discharge_reason', 'notes'
    ]
    VALID_STATUSES = ['active', 'on_hold', 'discharged', 'non_caseload']
    
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
        
        # Validate status
        status = data.get('status', '').lower()
        if status not in self.VALID_STATUSES:
            errors.append(f"status must be one of: {', '.join(self.VALID_STATUSES)}")
        else:
            data['status'] = status
        
        # Validate centre if provided
        centre_name = row.get('centre', '').strip()
        if centre_name:
            centre = self._lookup_centre(centre_name)
            if centre:
                data['centre'] = centre
            else:
                errors.append(f"Centre '{centre_name}' not found")
        
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
        
        # Validate discharge requirements
        if status == 'discharged':
            if not end_date:
                errors.append("end_date is required for discharged status")
            if not row.get('discharge_reason', '').strip():
                errors.append("discharge_reason is required for discharged status")
        
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
        for field in ['address_line1', 'address_line2', 'city', 'province', 'postal_code',
                      'guardian1_name', 'guardian1_phone', 'guardian2_name', 'guardian2_phone',
                      'discharge_reason', 'notes']:
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
                
                # Create child record
                child = Child(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    date_of_birth=data['date_of_birth'],
                    status=data['status'],
                    created_by=self.user,
                    updated_by=self.user
                )
                
                # Set optional fields
                if 'centre' in data:
                    child.centre = data['centre']
                if 'start_date' in data:
                    child.start_date = data['start_date']
                if 'end_date' in data:
                    child.end_date = data['end_date']
                
                # Set optional text fields
                for field in ['address_line1', 'address_line2', 'city', 'province', 'postal_code',
                              'guardian1_name', 'guardian1_phone', 'guardian1_email',
                              'guardian2_name', 'guardian2_phone', 'guardian2_email',
                              'discharge_reason', 'notes']:
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
        
        # Write headers
        headers = [
            'first_name', 'last_name', 'date_of_birth', 'status',
            'centre', 'guardian1_name', 'guardian1_phone', 'guardian1_email',
            'guardian2_name', 'guardian2_phone', 'guardian2_email',
            'address_line1', 'address_line2', 'city', 'province', 'postal_code',
            'start_date', 'end_date', 'discharge_reason', 'notes'
        ]
        writer.writerow(headers)
        
        # Write example rows
        examples = [
            ['John', 'Smith', '2015-03-15', 'active', 'Main Centre', 'Sarah Smith', '416-555-0123', 
             'sarah@example.com', '', '', '', '123 Main St', '', 'Toronto', 'ON', 'M1A 1A1', 
             '2024-01-01', '', '', 'New admission'],
            ['Jane', 'Doe', '2016-07-22', 'active', '', 'John Doe', '647-555-0456', 'john@example.com',
             'Mary Doe', '647-555-0789', 'mary@example.com', '456 Oak Ave', 'Unit 10', 'Mississauga', 
             'ON', 'L5A 1B2', '', '', '', ''],
            ['Bob', 'Johnson', '2014-11-30', 'non_caseload', '', '', '', '', '', '', '',
             '', '', '', 'ON', '', '2023-06-01', '', '', 'Assessment only'],
        ]
        
        for example in examples:
            writer.writerow(example)
        
        return output.getvalue()
