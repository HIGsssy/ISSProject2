"""
Management command to run interactive first-time setup.
Prompts for configuration and generates .env file.
"""
import os
import secrets
import sys
from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = 'Interactive first-time setup - generates .env configuration'

    def handle(self, *args, **options):
        """Run interactive setup."""
        
        # Check if .env exists and is configured
        env_path = '/app/.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                content = f.read()
                # Check if it has real values (not placeholders)
                if 'FIELD_ENCRYPTION_KEY=' in content and len(content) > 500:
                    self.stdout.write(self.style.SUCCESS(
                        '\n✓ Configuration already exists. Skipping setup.\n'
                    ))
                    return
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('ISS Portal - First Time Setup'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        self.stdout.write('Please provide the following configuration values:')
        self.stdout.write(self.style.WARNING('(Press Enter to use default value shown in brackets)\n'))
        
        # Collect configuration
        allowed_hosts = input('Domain/IP for ALLOWED_HOSTS [localhost]: ').strip() or 'localhost'
        db_name = input('Database name [iss_portal_db]: ').strip() or 'iss_portal_db'
        db_user = input('Database username [iss_user]: ').strip() or 'iss_user'
        
        # Password with confirmation
        while True:
            db_password = input('Database password (required): ').strip()
            if not db_password:
                self.stdout.write(self.style.ERROR('Password cannot be empty.'))
                continue
            db_password_confirm = input('Confirm password: ').strip()
            if db_password == db_password_confirm:
                break
            self.stdout.write(self.style.ERROR('Passwords do not match. Try again.'))
        
        tz_value = input('Timezone [America/Toronto]: ').strip() or 'America/Toronto'
        
        # Generate keys
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('Generating Security Keys...'))
        self.stdout.write('='*80 + '\n')
        
        self.stdout.write('Generating SECRET_KEY...')
        secret_key = secrets.token_urlsafe(50)
        self.stdout.write(self.style.SUCCESS('✓ SECRET_KEY generated\n'))
        
        self.stdout.write('Generating FIELD_ENCRYPTION_KEY...')
        encryption_key = Fernet.generate_key().decode()
        self.stdout.write(self.style.SUCCESS('✓ FIELD_ENCRYPTION_KEY generated\n'))
        
        # Create .env content
        env_content = f"""# ISS Portal Configuration
# Generated: {self.get_timestamp()}

# Django Settings
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS={allowed_hosts}

# Database
POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}

# Encryption (CRITICAL - Do not lose this key!)
FIELD_ENCRYPTION_KEY={encryption_key}

# Timezone
TZ={tz_value}

# Database Connection
DATABASE_URL=postgresql://{db_user}:{db_password}@db:5432/{db_name}

# Email Configuration (optional)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=your-email@example.com
# EMAIL_HOST_PASSWORD=your-email-password
"""
        
        # Write .env file
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        # Set permissions
        os.chmod(env_path, 0o600)
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('✓ Configuration Complete!'))
        self.stdout.write('='*80 + '\n')
        
        self.stdout.write(self.style.SUCCESS('Configuration Summary:'))
        self.stdout.write(f'  Domain/IP:      {allowed_hosts}')
        self.stdout.write(f'  Database:       {db_name}')
        self.stdout.write(f'  DB User:        {db_user}')
        self.stdout.write(f'  Timezone:       {tz_value}')
        self.stdout.write(f'  SECRET_KEY:     [generated]')
        self.stdout.write(f'  ENCRYPTION_KEY: [generated]\n')
        
        self.stdout.write(self.style.WARNING('⚠️  IMPORTANT:'))
        self.stdout.write('  - Configuration saved to /app/.env')
        self.stdout.write('  - Back up your FIELD_ENCRYPTION_KEY - data cannot be recovered without it!')
        self.stdout.write('  - Default admin credentials: admin / admin123')
        self.stdout.write(self.style.ERROR('  - CHANGE THE DEFAULT PASSWORD IMMEDIATELY!\n'))
        
        self.stdout.write('='*80 + '\n')
    
    def get_timestamp(self):
        """Get current timestamp."""
        from django.utils import timezone
        return timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
