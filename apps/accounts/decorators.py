"""Portão de bloqueio SUAVE: exige e-mail confirmado para interações sociais.

"Suave" porque nunca usa is_active=False para isto — ver o comentário em
apps.accounts.models.CustomUser.email_verified sobre por que os dois campos
não podem se confundir (is_active alimenta panels.can_access_admin e o
django-axes; é reservado para "conta desativada pelo administrador"). Aqui a
conta continua ativa e a pessoa continua logada; só fica impedida de
comentar/curtir/salvar até confirmar o e-mail.
"""

import functools

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

MENSAGEM_BLOQUEIO = 'Confirme seu e-mail para comentar, curtir e salvar artigos.'


def email_verified_required(view_func):
    """Bloqueia a view até o e-mail ser confirmado — com duas isenções.

    Deixa passar:
      * usuário não autenticado — quem resolve esse caso é o @login_required
        que vem ANTES deste decorator na pilha (ver apps/news/views.py); aqui
        só decidimos o que fazer quando JÁ existe um request.user autenticado.
      * request.user.email_verified — o caminho normal, pós-confirmação.
      * is_staff ou is_superuser — createsuperuser e usuários criados pelo
        admin nunca passam pelo fluxo de código (não há cadastro público
        disparando issue_code para eles). Sem esta isenção, a própria redação
        ficaria trancada fora dos comentários dos próprios artigos por causa
        de um campo pensado para leitor — regressão grave, não proteção extra.

    A view alvo é HTMX-aware (request.htmx, checado em apps/news/views.py) e
    este decorator precisa responder nos dois modos: HTMX espera um fragmento
    HTML pequeno para o swap; navegação normal espera um redirect com mensagem.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or user.email_verified or user.is_staff or user.is_superuser:
            return view_func(request, *args, **kwargs)

        if request.htmx:
            # 200, não 403: uma resposta HTMX com status de erro é DESCARTADA
            # pelo htmx por padrão (sem swap) — o aviso nunca chegaria a
            # aparecer na tela. 200 com um fragmento curto é o único jeito de
            # garantir que a pessoa VÊ por que a ação não aconteceu.
            verify_url = reverse('accounts:verify_email')
            fragment = (
                f'<p class="text-red-500 text-sm font-ui">{MENSAGEM_BLOQUEIO} '
                f'<a href="{verify_url}" class="underline font-bold">Confirmar agora</a></p>'
            )
            return HttpResponse(fragment)

        messages.error(request, MENSAGEM_BLOQUEIO)
        return redirect('accounts:verify_email')

    return wrapper
