"""
Context processors for injecting global template variables.
"""
from .models import ThemeSetting


def theme_settings(request):
    """
    Inject theme settings into all template contexts.
    
    Makes theme_settings and theme_css_variables available in templates.
    Caches the theme to avoid database hits on every request.
    """
    try:
        theme = ThemeSetting.get_theme()
        
        # CSS variables dict for easy template access
        css_vars = {
            'primary': theme.primary_color,
            'secondary': theme.secondary_color,
            'accent': theme.accent_color,
            'success': theme.success_color,
            'warning': theme.warning_color,
            'danger': theme.danger_color,
        }
        
        return {
            'theme_settings': theme,
            'theme_css_variables': css_vars,
        }
    except Exception as e:
        # Gracefully handle case where ThemeSetting table doesn't exist yet
        # (during migrations, for example)
        return {
            'theme_settings': None,
            'theme_css_variables': {},
        }
