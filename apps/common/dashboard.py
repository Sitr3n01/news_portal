"""Indicadores operacionais compartilhados pelo painel unificado.

Até a unificação, este módulo era o ``DASHBOARD_CALLBACK`` do Unfold e montava
a página inicial do /admin/. A página inicial agora é uma só — a visão geral em
``/painel/`` (apps/common/newsroom) — e o /admin/ redireciona para ela. Ficaram
aqui as peças operacionais que ela reaproveita: saúde do envio de e-mails e da
newsletter, e os atalhos para os guias de operação.
"""

from apps.common.admin_nav import (
    MANAGEMENT_PERMISSIONS,
    SCHOOL_PERMISSIONS,
)
from apps.common.admin_nav import admin_url as _admin_url
from apps.common.admin_nav import can_any as _can_any
from apps.common.admin_nav import get_email_status as _get_email_status

SCHOOL_GUIDE_PERMISSIONS = SCHOOL_PERMISSIONS
MANAGEMENT_GUIDE_PERMISSIONS = MANAGEMENT_PERMISSIONS


def _system_tone(email_status, newsletter_config_ready, newsletter_failed_deliveries):
    if newsletter_failed_deliveries:
        return 'danger'
    if not email_status['smtp_configured'] or not newsletter_config_ready:
        return 'warning'
    return 'success'


def build_guide_links(user):
    """Guias de operação que o usuário alcança (eles vivem atrás da porta do /admin/)."""
    links = []
    if _can_any(user, SCHOOL_GUIDE_PERMISSIONS):
        links.append({
            'title': 'Guia Komuniki',
            'route': 'admin_school_guide',
            'icon': 'book',
            'url': _admin_url('admin_school_guide'),
            'hint': 'Home, cursos, blocos, depoimentos e mensagens em um fluxo guiado.',
        })
    if _can_any(user, MANAGEMENT_GUIDE_PERMISSIONS):
        links.append({
            'title': 'Guia de Gerenciamento',
            'route': 'admin_management_guide',
            'icon': 'shield',
            'url': _admin_url('admin_management_guide'),
            'hint': 'Usuários, permissões, mídia, remetentes e saúde do sistema.',
        })
    return links


def build_system_health(user):
    """Saúde do envio de e-mails e da newsletter.

    Os detalhes técnicos (host, backend, itens ausentes) seguem restritos a
    superusuário, como no dashboard anterior do /admin/.
    """
    from apps.common.models import SiteExtension
    from apps.news.models import NewsletterDelivery

    email_status = _get_email_status()
    configured_sender_sites = SiteExtension.objects.exclude(newsletter_from_email='').count()
    newsletter_pending_deliveries = NewsletterDelivery.objects.filter(
        status=NewsletterDelivery.Status.PENDING,
    ).count()
    newsletter_failed_deliveries = NewsletterDelivery.objects.filter(
        status=NewsletterDelivery.Status.FAILED,
    ).count()

    newsletter_config_ready = email_status['smtp_configured'] and configured_sender_sites > 0
    if not email_status['smtp_configured']:
        hint = 'Configure o servidor de e-mail para liberar envios automáticos.'
    elif not configured_sender_sites:
        hint = 'Defina um remetente de newsletter nas configurações dos sites.'
    else:
        hint = 'Envio de e-mails e remetentes estão prontos.'

    tone = _system_tone(email_status, newsletter_config_ready, newsletter_failed_deliveries)
    status = {
        'danger': 'Falha de envio',
        'warning': 'Configuração incompleta',
        'success': 'Tudo saudável',
    }[tone]

    return {
        'tone': tone,
        'status': status,
        'hint': hint,
        'can_view_details': user.is_superuser,
        'metrics': [
            {
                'label': 'Envio de e-mails',
                'value': 'Pronto' if email_status['smtp_configured'] else 'Atenção',
                'tone': 'success' if email_status['smtp_configured'] else 'warning',
            },
            {
                'label': 'Remetentes configurados',
                'value': configured_sender_sites,
                'tone': 'success' if configured_sender_sites else 'warning',
            },
            {
                'label': 'Entregas pendentes',
                'value': newsletter_pending_deliveries,
                'tone': 'warning' if newsletter_pending_deliveries else 'neutral',
            },
            {
                'label': 'Falhas de newsletter',
                'value': newsletter_failed_deliveries,
                'tone': 'danger' if newsletter_failed_deliveries else 'neutral',
            },
        ],
        'details': [
            {'label': 'Servidor de e-mail', 'value': f"{email_status['email_host']}:{email_status['email_port']}"},
            {'label': 'Backend técnico', 'value': email_status['email_backend']},
            {'label': 'Itens técnicos ausentes', 'value': email_status['email_missing_settings'] or 'Nenhum'},
        ],
    }
