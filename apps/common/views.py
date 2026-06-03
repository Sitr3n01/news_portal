from django.http import HttpResponse


def health_check(request):
    """Liveness probe para Docker/orquestradores.

    Sem dependência de banco de propósito: responde 200 enquanto o processo da
    aplicação estiver de pé (liveness, não readiness). Em produção, a rota é
    isenta do redirect HTTPS via ``SECURE_REDIRECT_EXEMPT`` para que a probe
    interna do container (HTTP, sem proxy) não receba 301.
    """
    return HttpResponse('ok', content_type='text/plain')
