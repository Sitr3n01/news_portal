import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

TURNSTILE_RESPONSE_FIELD = 'cf-turnstile-response'
TURNSTILE_SITEVERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
TURNSTILE_TEST_SITE_KEY = '1x00000000000000000000AA'
TURNSTILE_TEST_SECRET_KEY = '1x0000000000000000000000000000000AA'

logger = logging.getLogger(__name__)


def get_turnstile_site_key():
    site_key = getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
    if site_key:
        return site_key
    if settings.DEBUG:
        return TURNSTILE_TEST_SITE_KEY
    return ''


def get_turnstile_secret_key():
    secret_key = getattr(settings, 'CLOUDFLARE_TURNSTILE_SECRET_KEY', '')
    if secret_key:
        return secret_key
    if settings.DEBUG:
        return TURNSTILE_TEST_SECRET_KEY
    return ''


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',', 1)[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def verify_turnstile(token, remote_ip=''):
    token = str(token or '').strip()
    secret_key = get_turnstile_secret_key()
    if not token or not secret_key:
        return False

    payload = {
        'secret': secret_key,
        'response': token,
    }
    if remote_ip:
        payload['remoteip'] = remote_ip

    request = Request(
        TURNSTILE_SITEVERIFY_URL,
        data=urlencode(payload).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    timeout = getattr(settings, 'CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT', 5)

    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.warning('Falha ao validar Cloudflare Turnstile: %s', exc)
        return False

    return bool(data.get('success'))
