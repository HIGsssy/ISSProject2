"""
Management command to generate encryption key for field-level encryption.
"""
from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = 'Generate a new encryption key for field encryption'

    def handle(self, *args, **options):
        key = Fernet.generate_key().decode()
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('Generated Encryption Key'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'\nFIELD_ENCRYPTION_KEY={key}\n')
        self.stdout.write(self.style.WARNING('\nIMPORTANT:'))
        self.stdout.write('1. Add this to your .env file')
        self.stdout.write('2. Keep this key secure - loss means data cannot be decrypted')
        self.stdout.write('3. Use environment variables or secrets manager in production')
        self.stdout.write('4. Restart your application after adding the key')
        self.stdout.write(self.style.SUCCESS('\n' + '='*70 + '\n'))
