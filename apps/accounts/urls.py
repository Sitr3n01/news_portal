from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import code_views, oauth_views, views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),

    # Login com Google. Fica sob `accounts:` — e não sob `panel:` — porque
    # atende as DUAS portas: o botão aparece tanto no login do leitor quanto no
    # dos painéis, e quem decide onde a pessoa aterrissa é panels.post_login_target,
    # não a rota por onde ela entrou. Sem credencial configurada, as duas
    # devolvem 404 (ver oauth_views._require_enabled).
    path('google/', oauth_views.google_start, name='google_start'),
    path('google/callback/', oauth_views.google_callback, name='google_callback'),
    # settings.LOGOUT_REDIRECT_URL (hoje 'news:list'), não a string literal
    # '/news/': panel_logout (apps/accounts/panel_views.py) já resolve o
    # destino por essa mesma setting, e a string fixa aqui era a única
    # divergência entre os dois logouts do projeto.
    path('logout/', auth_views.LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('register/', views.register_view, name='register'),

    path('confirmar-email/', code_views.verify_email, name='verify_email'),
    path('confirmar-email/reenviar/', code_views.resend_verification_code, name='resend_verification_code'),

    path('profile/', views.update_profile, name='update_profile'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('toggle-newsletter/', views.toggle_newsletter, name='toggle_newsletter'),

    # O nome `password_reset` é mantido de propósito: templates/accounts/login.html,
    # templates/auth/login.html e as rotas-sombra de /admin/password_reset/ e
    # /cms/password_reset/ (config/urls.py) já apontam para ele, então trocar a
    # view por dentro migra todos de uma vez, sem caçar link em template.
    path('password_reset/', code_views.password_reset_request, name='password_reset'),
    path('senha/codigo/', code_views.password_reset_code, name='password_reset_code'),
    path('senha/reenviar/', code_views.password_reset_resend, name='password_reset_resend'),
    path('senha/nova/', code_views.password_reset_new, name='password_reset_new'),

    # Fluxo ANTIGO por link: não é mais gerado por ninguém (a view que enviava
    # os e-mails com link foi removida), mas as duas rotas abaixo continuam de
    # pé para que um link já enviado, ainda dentro do PASSWORD_RESET_TIMEOUT,
    # não caia em 404 na cara de quem clicou.
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset/password_reset_confirm.html',
            success_url='/accounts/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset/password_reset_complete.html'), name='password_reset_complete'),
]

