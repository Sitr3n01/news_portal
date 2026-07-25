"""Login unificado, escolha de área, aviso de acesso negado e logout único.

Sobre CBV: docs/ai/development_rules.md §2 manda usar Function-Based View. A
exceção — registrada na própria regra — são as views de autenticação do Django,
que já são CBV por natureza. Reescrever LoginView à mão significaria reimplantar
o tratamento de sessão e o backend de autenticação, o que é regressão de
segurança e não ganho de estilo. As três views que não vêm do Django
(``panel_picker``, ``no_access``, ``panel_logout``) são FBV.
"""

import logging

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts import panels
from apps.accounts.panel_forms import PanelLoginForm

security_log = logging.getLogger('apps.security')


class PanelLoginView(LoginView):
    """Porta única de Publicação de matérias e Administração do sistema."""

    template_name = 'auth/login.html'
    authentication_form = PanelLoginForm

    # Deliberadamente False: a implementação do Django levanta ValueError
    # ("Redirection loop for authenticated user") quando o destino coincide com
    # a própria tela de login, e não sabe distinguir "já autenticado, mas para o
    # painel errado". O tratamento fica no get() abaixo.
    redirect_authenticated_user = False

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(
                panels.post_login_target(
                    request.user, request, next_url=self.get_redirect_url(),
                )
            )
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # A escolha precisa ser guardada ANTES do super(): LoginView.form_valid
        # chama get_success_url() sem acesso ao formulário.
        self._chosen_panel = form.cleaned_data.get('panel') or ''
        response = super().form_valid(form)
        if not form.cleaned_data.get('remember'):
            self.request.session.set_expiry(0)
        return response

    def get_success_url(self):
        return panels.post_login_target(
            self.request.user,
            self.request,
            # get_redirect_url() já valida host e esquema (RedirectURLMixin).
            next_url=self.get_redirect_url(),
            chosen_panel=getattr(self, '_chosen_panel', ''),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel_cards'] = panels.panel_cards(None)
        return context


@login_required(login_url='panel:login')
@require_http_methods(['GET'])
def panel_picker(request):
    """Escolha de área, para quem alcança as duas.

    Também é o destino permanente do "trocar de área" a partir de qualquer
    painel — por isso continua acessível mesmo com um só painel disponível
    (nesse caso entra direto, para não virar uma tela de um botão só).
    """
    available = panels.available_panels(request.user)

    if not available:
        return redirect('panel:no_access')
    if len(available) == 1:
        return redirect(panels.panel_url(available[0]))

    return render(request, 'auth/panel_picker.html', {
        'panel_cards': [card for card in panels.panel_cards(request.user) if card['allowed']],
    })


@require_http_methods(['GET'])
def no_access(request):
    """Explica, em português claro, por que a área pedida não abriu.

    Devolve 403 — é uma recusa, não uma página comum. Usuário anônimo é mandado
    ao login: para quem não se identificou, nem a existência da área é revelada.
    """
    if not request.user.is_authenticated:
        return redirect('panel:login')

    requested = request.GET.get('painel', '')
    if requested not in panels.PANEL_ORDER:
        requested = ''

    available = [card for card in panels.panel_cards(request.user) if card['allowed']]

    security_log.warning(
        'AUTH_PANEL_DENIED user_id=%s requested_panel=%s',
        request.user.pk, requested or '-',
    )

    return render(request, 'auth/no_access.html', {
        'requested_label': panels.panel_label(requested),
        'panel_cards': available,
        'role_label': request.user.get_role_display(),
    }, status=403)


@require_http_methods(['GET', 'POST'])
def panel_logout(request):
    """Encerra a sessão da plataforma inteira.

    O MESMO callable atende /sair/, /admin/logout/ e /cms/logout/, para que sair
    de uma área encerre todas — há uma única sessão do Django por trás das três.

    Precisa ser view de verdade, e não RedirectView: o LogoutView do Django 5 só
    aceita POST, e um 302 sobre um POST vira GET no caminho, deixando o usuário
    conectado. Os três botões de sair já enviam POST com CSRF.
    """
    if request.method == 'GET':
        # GET nunca altera estado. Links e favoritos antigos caem no login.
        return redirect('panel:login')

    logout(request)

    next_url = request.POST.get('next') or ''
    if not (next_url and panels.is_safe_next(next_url, request)):
        # Quem saiu de dentro de um painel volta para o login dos painéis; quem
        # saiu do site público volta para o site público.
        next_url = (
            reverse('panel:login')
            if panels.panel_for_url(request.path)
            else resolve_url(settings.LOGOUT_REDIRECT_URL)
        )

    response = redirect(next_url)
    # Apagar o cookie explicitamente (mesma abordagem do LogoutView do Wagtail):
    # sem isso o logout emite um sessionid novo, e caches de borda usam
    # "sem sessionid ⇒ conteúdo cacheável" como sinal.
    response.delete_cookie(
        settings.SESSION_COOKIE_NAME,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
    )
    request.session.modified = False
    return response
