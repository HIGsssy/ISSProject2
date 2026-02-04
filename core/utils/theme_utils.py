"""
Utility functions for theme management and CSS generation.
"""

from PIL import Image
import os
from django.conf import settings


def validate_color_hex(color_string):
    """
    Validate that a color string is a valid hex color.
    
    Args:
        color_string: String in format '#RRGGBB' or 'RRGGBB'
    
    Returns:
        bool: True if valid hex color
    """
    color_string = color_string.lstrip('#')
    if len(color_string) != 6:
        return False
    try:
        int(color_string, 16)
        return True
    except ValueError:
        return False


def validate_image_upload(image_file, max_size_mb=2, allowed_formats=None):
    """
    Validate uploaded image file.
    
    Args:
        image_file: File object from form upload
        max_size_mb: Maximum file size in megabytes (default: 2)
        allowed_formats: List of allowed formats (default: JPEG, PNG, WebP)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if allowed_formats is None:
        allowed_formats = ['JPEG', 'PNG', 'WEBP']
    
    # Check file size
    if image_file.size > max_size_mb * 1024 * 1024:
        return False, f'Image size exceeds {max_size_mb}MB limit'
    
    # Check image format
    try:
        img = Image.open(image_file)
        if img.format not in allowed_formats:
            return False, f'Invalid format. Allowed: {", ".join(allowed_formats)}'
        
        return True, None
    except Exception as e:
        return False, f'Invalid image file: {str(e)}'


def optimize_image(image_file, output_format='WEBP', quality=85, max_width=2000, max_height=2000):
    """
    Optimize image for web use.
    
    Args:
        image_file: PIL Image object or file path
        output_format: Output format (default: WEBP)
        quality: JPEG/WebP quality 0-100 (default: 85)
        max_width: Maximum width in pixels (default: 2000)
        max_height: Maximum height in pixels (default: 2000)
    
    Returns:
        Image: Optimized PIL Image object
    """
    if isinstance(image_file, str):
        img = Image.open(image_file)
    else:
        img = Image.open(image_file)
    
    # Convert RGBA to RGB if needed for JPEG
    if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Resize if needed (maintain aspect ratio)
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    return img


def get_color_palette():
    """
    Get the current color palette from ThemeSetting.
    
    Returns:
        dict: Color palette with keys: primary, secondary, accent, success, warning, danger
    """
    from core.models import ThemeSetting
    
    try:
        theme = ThemeSetting.get_theme()
        return {
            'primary': theme.primary_color,
            'secondary': theme.secondary_color,
            'accent': theme.accent_color,
            'success': theme.success_color,
            'warning': theme.warning_color,
            'danger': theme.danger_color,
        }
    except:
        # Return default colors if theme not available
        return {
            'primary': '#3b82f6',
            'secondary': '#8b5cf6',
            'accent': '#10b981',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
        }


def generate_theme_css_variables(theme_obj):
    """
    Generate CSS variable declarations from theme object.
    
    Args:
        theme_obj: ThemeSetting instance
    
    Returns:
        str: CSS variable declarations
    """
    return f"""
:root {{
    --primary: {theme_obj.primary_color};
    --secondary: {theme_obj.secondary_color};
    --accent: {theme_obj.accent_color};
    --success: {theme_obj.success_color};
    --warning: {theme_obj.warning_color};
    --danger: {theme_obj.danger_color};
}}
"""
