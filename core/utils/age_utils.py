"""Utilities for age category and age calculation."""
from dateutil.relativedelta import relativedelta
from django.utils import timezone


def calculate_age_in_months(date_of_birth, reference_date=None):
    """Calculate age in months from date of birth.
    
    Args:
        date_of_birth: DateField value
        reference_date: Date to calculate age at (defaults to today)
    
    Returns:
        int: Age in months
    """
    if reference_date is None:
        reference_date = timezone.now().date()
    
    age_delta = relativedelta(reference_date, date_of_birth)
    return age_delta.years * 12 + age_delta.months


def get_age_group(age_in_months):
    """Determine age group based on age in months.
    
    Categories:
    - infant: 0-18 months
    - toddler: 18-30 months
    - preschooler: 30-45.6 months (3.8 years)
    - jk_sk: 45.6-72 months (6 years)
    - school_age: 72-144 months (12 years)
    - other: 144+ months
    
    Args:
        age_in_months: Age in months (can be decimal for precision)
    
    Returns:
        str: Category name ('infant', 'toddler', 'preschooler', 'jk_sk', 'school_age', 'other')
    """
    if age_in_months <= 18:
        return 'infant'
    elif age_in_months < 30:
        return 'toddler'
    elif age_in_months <= 45.6:  # 3.8 years
        return 'preschooler'
    elif age_in_months < 72:  # 6 years
        return 'jk_sk'
    elif age_in_months < 144:  # 12 years
        return 'school_age'
    else:
        return 'other'
