import logging

from axes.helpers import get_client_ip_address, get_client_user_agent
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_delete, post_migrate
from django.dispatch import receiver

from .admin_roles import ensure_admin_role_groups
from .models import CustomUser
from .panels import available_panels

# Herda o handler de console do logger 'apps' (config/settings/base.py), que
# escreve em stdout — contrato 12-factor do projeto. Nenhuma configuração extra.
security_log = logging.getLogger('apps.security')


@receiver(post_migrate, dispatch_uid='accounts.ensure_admin_role_groups')
def create_admin_role_groups(sender, **kwargs):
    ensure_admin_role_groups()


# ── Auditoria de eventos de autenticação ───────────────────────────────────
#
# NUNCA registrar senha, chave de sessão, token CSRF, uidb64/token de
# recuperação ou o link completo de redefinição.
#
# Todo receptor engole exceções: uma falha ao gravar log jamais pode impedir
# alguém de entrar ou sair.

def _request_meta(request):
    if request is None:
        return '-', '-', '-'
    ip = get_client_ip_address(request) or '-'
    # User agent é entrada de terceiros: truncar e usar repr para não deixar
    # quebra de linha forjar uma entrada de log falsa.
    user_agent = repr((get_client_user_agent(request) or '-')[:200])
    return ip, user_agent, request.path


def _safe_username(value):
    """Username é controlado por quem tenta entrar — sanitizar sempre.

    Sem isso, enviar "admin\nAUTH_LOGIN_OK user_id=1" forjaria uma linha de log.
    """
    return repr(str(value or '-')[:150])


@receiver(user_logged_in, dispatch_uid='accounts.security_log_login')
def log_login_success(sender, request, user, **kwargs):
    try:
        ip, user_agent, path = _request_meta(request)
        security_log.info(
            'AUTH_LOGIN_OK user_id=%s username=%s is_staff=%s panels=%s ip=%s path=%s ua=%s',
            user.pk, _safe_username(user.get_username()), user.is_staff,
            ','.join(available_panels(user)) or '-', ip, path, user_agent,
        )
    except Exception:
        pass


@receiver(user_logged_out, dispatch_uid='accounts.security_log_logout')
def log_logout(sender, request, user, **kwargs):
    try:
        ip, _, path = _request_meta(request)
        security_log.info(
            'AUTH_LOGOUT user_id=%s username=%s ip=%s path=%s',
            getattr(user, 'pk', None),
            _safe_username(user.get_username() if user else None),
            ip, path,
        )
    except Exception:
        pass


@receiver(user_login_failed, dispatch_uid='accounts.security_log_login_failed')
def log_login_failed(sender, credentials, request=None, **kwargs):
    try:
        ip, user_agent, path = _request_meta(request)
        # O Django já substitui a senha por '********' em credentials, mas por
        # segurança só o username é lido daqui.
        security_log.warning(
            'AUTH_LOGIN_FAIL username=%s ip=%s path=%s ua=%s',
            _safe_username((credentials or {}).get('username')), ip, path, user_agent,
        )
    except Exception:
        pass


@receiver(post_delete, sender=CustomUser, dispatch_uid='accounts.delete_avatar_file')
def delete_avatar_file(sender, instance, **kwargs):
    """Remove o arquivo do avatar do disco quando a conta é excluída,
    evitando arquivos órfãos no volume de mídia (limite de 50GB da VPS)."""
    avatar = instance.avatar
    if avatar:
        try:
            avatar.delete(save=False)
        except Exception:
            pass
