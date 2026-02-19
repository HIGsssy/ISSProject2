"""Management command to backfill historical age progression events."""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import Child, AgeProgressionEvent
from core.utils.age_utils import calculate_age_in_months, get_age_group
from datetime import timedelta


class Command(BaseCommand):
    help = 'Backfill age progression events for children based on date of birth calculations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months to backfill (default: 6)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating events'
        )

    def handle(self, *args, **options):
        months = options['months']
        dry_run = options['dry_run']
        
        self.stdout.write(f"Starting age progression backfill (last {months} months)")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No events will be created"))
        
        # Get all active and discharged children
        children = Child.objects.filter(
            date_of_birth__isnull=False
        ).order_by('id')
        
        total_children = children.count()
        total_events_created = 0
        transition_counts = {}
        
        today = timezone.now().date()
        
        for idx, child in enumerate(children, 1):
            # Progress output every 50 children
            if idx % 50 == 0:
                self.stdout.write(f"Processing child {idx} of {total_children}...")
            
            # Skip if child is too young (less than 1 month old)
            if child.date_of_birth > today - timedelta(days=30):
                continue
            
            # Iterate backwards through months from today to months ago
            previous_category = None
            
            for month_offset in range(months + 1):
                # Sample on the 1st of each month (calendar month start)
                sample_date = (today - relativedelta(months=month_offset)).replace(day=1)
                
                # Skip if before the child's birth date
                if sample_date < child.date_of_birth:
                    break
                
                # Calculate age at that month
                age_in_months = calculate_age_in_months(child.date_of_birth, sample_date)
                current_category = get_age_group(age_in_months)
                
                # Check if this is a transition from previous month
                if previous_category is not None and current_category != previous_category:
                    # Determine if this is an upward transition
                    category_order = ['infant', 'toddler', 'preschooler', 'jk_sk', 'school_age', 'other']
                    new_idx = category_order.index(current_category) if current_category in category_order else -1
                    prev_idx = category_order.index(previous_category) if previous_category in category_order else -1
                    
                    if new_idx > prev_idx:  # Upward transition
                        # Check if event already exists (idempotent)
                        existing = AgeProgressionEvent.objects.filter(
                            child=child,
                            transition_date=sample_date,
                            previous_category=previous_category,
                            new_category=current_category
                        ).exists()
                        
                        if not existing:
                            if not dry_run:
                                AgeProgressionEvent.objects.create(
                                    child=child,
                                    previous_category=previous_category,
                                    new_category=current_category,
                                    transition_date=sample_date,
                                    age_in_months=age_in_months
                                )
                            
                            transition_key = f"{previous_category} → {current_category}"
                            transition_counts[transition_key] = transition_counts.get(transition_key, 0) + 1
                            total_events_created += 1
                            
                            if dry_run:
                                self.stdout.write(
                                    f"  [DRY RUN] Would create: {child.full_name} → {transition_key} on {sample_date}"
                                )
                
                previous_category = current_category
        
        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Backfill complete!"))
        self.stdout.write(f"Total events {'would be created' if dry_run else 'created'}: {total_events_created}")
        self.stdout.write("\nBreakdown by transition type:")
        
        for transition, count in sorted(transition_counts.items()):
            self.stdout.write(f"  {transition}: {count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No changes were made to the database."))
