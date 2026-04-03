"""
Constantes e utilidades centralizadas de sanitização HTML (bleach).

Usado por:
- apps/news/models.py (Article.save)
- apps/school/models.py (Page.save)
- apps/common/templatetags/sanitize.py (template filter)
"""
from urllib.parse import urlparse

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u',
    'ul', 'ol', 'li',
    'a', 'abbr',
    'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'pre', 'code',
    'img', 'figure', 'figcaption',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span', 'hr',
    'iframe',  # para embeds — restrito a YouTube por _validate_iframe_attr()
]

# Domínios permitidos para iframe src (apenas YouTube)
ALLOWED_IFRAME_HOSTS = {
    'www.youtube.com',
    'youtube.com',
    'www.youtube-nocookie.com',
    'youtube-nocookie.com',
}


def _validate_iframe_attr(tag, name, value):
    """Callback do bleach para validar atributos de iframe.
    Restringe src apenas a domínios YouTube."""
    if name in ('width', 'height', 'frameborder', 'allowfullscreen'):
        return True
    if name == 'allow':
        return True
    if name == 'src':
        try:
            parsed = urlparse(value)
            return parsed.scheme in ('http', 'https') and parsed.netloc in ALLOWED_IFRAME_HOSTS
        except Exception:
            return False
    return False


# Propriedades CSS seguras — bloqueia position, background-image, etc.
CSS_SANITIZER = CSSSanitizer(allowed_css_properties=[
    'color', 'background-color',
    'font-weight', 'font-style', 'font-size',
    'text-align', 'text-decoration', 'line-height',
    'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
    'border', 'border-radius',
    'width', 'max-width', 'height',
    'display',
])

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'loading', 'class'],
    'iframe': _validate_iframe_attr,
    'div': ['class', 'style'],
    'span': ['class', 'style'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    'p': ['class'],
    'h2': ['class', 'id'],
    'h3': ['class', 'id'],
    'h4': ['class', 'id'],
    'pre': ['class'],
    'code': ['class'],
    'blockquote': ['class'],
    'figure': ['class'],
}


def sanitize_content(value):
    """Sanitiza HTML removendo tags/atributos perigosos, preservando formatação editorial."""
    if not value:
        return ''
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        css_sanitizer=CSS_SANITIZER,
    )
