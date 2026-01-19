"""
Management command to create initial data for the ISS Portal.
Creates visit types and prompts for admin user creation.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import VisitType

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates initial data for ISS Portal (visit types, admin user)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating initial data for ISS Portal...'))
        
        # Create Visit Types
        self.create_visit_types()
        
        # Check for existing admin user
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING('\nNo admin user found.'))
            create_admin = input('Create admin user now? (yes/no): ').lower()
            
            if create_admin == 'yes':
                self.create_admin_user()
        else:
            self.stdout.write(self.style.SUCCESS('\nAdmin user already exists.'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Initial data creation complete!'))
    
    def create_visit_types(self):
        """Create default visit types."""
        visit_types = [
            {
                'name': 'Assessment',
                'description': 'Initial or ongoing assessment of child needs',
                'is_active': True
            },
            {
                'name': 'Regular Visit',
                'description': 'Standard support visit',
                'is_active': True
            },
            {
                'name': 'Other',
                'description': 'Other types of visits',
                'is_active': True
            }
        ]
        
        self.stdout.write('\nCreating visit types...')
        
        for vt_data in visit_types:
            visit_type, created = VisitType.objects.get_or_create(
                name=vt_data['name'],
                defaults={
                    'description': vt_data['description'],
                    'is_active': vt_data['is_active']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created visit type: {visit_type.name}'))
            else:
                self.stdout.write(f'  - Visit type already exists: {visit_type.name}')
    
    def create_admin_user(self):
        """Create admin user interactively."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.WARNING('CREATE ADMIN USER'))
        self.stdout.write('='*50 + '\n')
        
        username = input('Username: ').strip()
        if not username:
            self.stdout.write(self.style.ERROR('Username cannot be empty. Skipping admin creation.'))
            return
        
        email = input('Email: ').strip()
        first_name = input('First name: ').strip()
        last_name = input('Last name: ').strip()
        
        password = None
        while not password:
            password = input('Password: ').strip()
            if not password:
                self.stdout.write(self.style.ERROR('Password cannot be empty.'))
                continue
            
            password_confirm = input('Password (confirm): ').strip()
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                password = None
        
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                user.role = 'admin'
                user.save()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Admin user created successfully: {username}'))
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Name: {first_name} {last_name}')
            self.stdout.write(f'  Role: Administrator')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error creating admin user: {str(e)}'))
