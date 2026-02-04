"""
Django management command to rebuild Tailwind CSS.
Useful for development or when theme colors need to be recompiled.
"""

from django.core.management.base import BaseCommand, CommandError
import subprocess
import os
import sys


class Command(BaseCommand):
    help = 'Rebuild Tailwind CSS. Useful after theme color changes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch for file changes and rebuild automatically',
        )

    def handle(self, *args, **options):
        """Execute npm script to rebuild Tailwind CSS."""
        
        project_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )
        
        try:
            # Check if package.json exists
            package_json = os.path.join(project_root, 'package.json')
            if not os.path.exists(package_json):
                raise CommandError(
                    f'package.json not found in {project_root}. '
                    'Please ensure Node.js dependencies are set up.'
                )
            
            # Build or watch CSS
            if options['watch']:
                self.stdout.write(
                    self.style.SUCCESS('Watching for changes and rebuilding CSS...')
                )
                script = 'watch:css'
            else:
                self.stdout.write(
                    self.style.SUCCESS('Building Tailwind CSS...')
                )
                script = 'build:css'
            
            # Run npm script
            result = subprocess.run(
                ['npm', 'run', script],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise CommandError(
                    f'Failed to build CSS. Error: {result.stderr}'
                )
            
            if result.stdout:
                self.stdout.write(result.stdout)
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully rebuilt Tailwind CSS!'
                )
            )
            
        except subprocess.CalledProcessError as e:
            raise CommandError(
                f'Error running npm script: {e.stderr}'
            )
        except FileNotFoundError:
            raise CommandError(
                'npm not found. Please ensure Node.js is installed and in PATH.'
            )
