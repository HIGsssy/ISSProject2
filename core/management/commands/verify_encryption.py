"""
Management command to verify that encrypted fields are properly encrypted in the database.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from core.models import Child


class Command(BaseCommand):
    help = 'Verify that encrypted fields are properly encrypted in the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '=' * 80))
        self.stdout.write(self.style.WARNING('ENCRYPTION VERIFICATION'))
        self.stdout.write(self.style.WARNING('=' * 80 + '\n'))
        
        # Check model field types
        self.stdout.write('1. Checking Child model field types...\n')
        
        encrypted_field_types = []
        for field in Child._meta.get_fields():
            field_type = type(field).__name__
            if 'Encrypted' in field_type:
                encrypted_field_types.append((field.name, field_type))
        
        if encrypted_field_types:
            self.stdout.write(self.style.SUCCESS(f'   ✅ Found {len(encrypted_field_types)} encrypted field types defined'))
            for field_name, field_type in encrypted_field_types[:5]:
                self.stdout.write(f'      • {field_name}: {field_type}')
            if len(encrypted_field_types) > 5:
                self.stdout.write(f'      ... and {len(encrypted_field_types) - 5} more')
        else:
            self.stdout.write(self.style.ERROR('   ❌ No encrypted field types found!'))
        
        self.stdout.write('')
        
        # Check actual data
        self.stdout.write('2. Checking database encryption...\n')
        
        # Find children with data
        children_with_data = Child.objects.exclude(
            guardian1_name=''
        ).exclude(
            guardian1_name__isnull=True
        )[:5]
        
        if not children_with_data:
            self.stdout.write(self.style.WARNING('   ⚠️  No child records with guardian data found'))
            self.stdout.write('   To test: Add a child through the intake form or import CSV\n')
            
            # Try to find ANY child record
            any_child = Child.objects.first()
            if any_child:
                self.stdout.write(f'   Found child record (ID: {any_child.id}) but no encrypted data to test\n')
        else:
            self.stdout.write(f'   Testing {len(children_with_data)} child record(s)...\n')
            
            total_tested = 0
            total_encrypted = 0
            
            for child in children_with_data:
                # Get raw database values
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            guardian1_name, guardian1_cell_phone, guardian1_email,
                            address_line1, city, postal_code,
                            referral_source_name, referral_reason_details,
                            notes, alternate_location
                        FROM core_child 
                        WHERE id = %s
                    """, [child.id])
                    raw_row = cursor.fetchone()
                
                # Test fields that have data
                test_fields = [
                    ('guardian1_name', child.guardian1_name, raw_row[0]),
                    ('guardian1_cell_phone', child.guardian1_cell_phone, raw_row[1]),
                    ('guardian1_email', child.guardian1_email, raw_row[2]),
                    ('address_line1', child.address_line1, raw_row[3]),
                    ('city', child.city, raw_row[4]),
                    ('postal_code', child.postal_code, raw_row[5]),
                    ('referral_source_name', child.referral_source_name, raw_row[6]),
                    ('referral_reason_details', child.referral_reason_details, raw_row[7]),
                    ('notes', child.notes, raw_row[8]),
                    ('alternate_location', child.alternate_location, raw_row[9]),
                ]
                
                child_tested = 0
                child_encrypted = 0
                
                for field_name, decrypted_value, raw_value in test_fields:
                    if decrypted_value:  # Only test fields with data
                        child_tested += 1
                        total_tested += 1
                        
                        # Fernet encrypted data starts with 'gAAAAA' (base64 encoded)
                        is_encrypted = raw_value and isinstance(raw_value, str) and raw_value.startswith('gAAAAA')
                        
                        if is_encrypted:
                            child_encrypted += 1
                            total_encrypted += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR(f'      ❌ {field_name} (Child ID {child.id}): NOT ENCRYPTED!')
                            )
                            self.stdout.write(f'         Decrypted: {decrypted_value[:40]}...')
                            self.stdout.write(f'         Raw DB: {raw_value[:50]}...')
                
                if child_tested > 0:
                    if child_encrypted == child_tested:
                        self.stdout.write(
                            self.style.SUCCESS(f'   ✅ Child ID {child.id}: {child_encrypted}/{child_tested} fields encrypted')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ Child ID {child.id}: Only {child_encrypted}/{child_tested} fields encrypted!')
                        )
            
            # Summary
            self.stdout.write('\n' + '-' * 80)
            if total_tested == 0:
                self.stdout.write(self.style.WARNING('No fields with data to test'))
            elif total_encrypted == total_tested:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ SUCCESS: All {total_tested} tested fields are ENCRYPTED!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ WARNING: Only {total_encrypted}/{total_tested} fields are encrypted!')
                )
            self.stdout.write('-' * 80 + '\n')
        
        # Instructions
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('ENCRYPTION KEY INFORMATION')
        self.stdout.write('=' * 80)
        self.stdout.write('Encryption key location: Set via FIELD_ENCRYPTION_KEY environment variable')
        self.stdout.write('Key format: Fernet key (base64-encoded 32-byte key)')
        self.stdout.write('Field types: EncryptedCharField, EncryptedTextField, EncryptedEmailField')
        self.stdout.write('=' * 80 + '\n')
