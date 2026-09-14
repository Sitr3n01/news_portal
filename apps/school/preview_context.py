from django.conf import settings


def design_preview(request):
    """Only registered by config.settings.design_preview."""
    return {
        'design_preview': True,
        'design_preview_demo': settings.DESIGN_PREVIEW_SCENARIO == 'demo',
    }
