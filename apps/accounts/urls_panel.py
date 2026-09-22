"""Rotas do acesso administrativo unificado.

Montadas na raiz (cada padrão carrega o caminho completo) para que fiquem
legíveis em português — /entrar/, /sair/ — mas continuem morando num módulo de
aplicação. Ver a ordem exigida em config/urls.py.
"""

from django.urls import path

from apps.accounts import panel_views
from apps.common.newsroom import views as newsroom_views

app_name = 'panel'

urlpatterns = [
    path('entrar/', panel_views.PanelLoginView.as_view(), name='login'),
    path('sair/', panel_views.panel_logout, name='logout'),
    # /painel/ era a tela de escolha entre as duas áreas; com o painel
    # unificado, passa a ser a visão geral — a escolha virou a própria
    # navegação. `panel:picker` continua resolvendo para o mesmo endereço
    # (a primeira entrada vence na resolução; as duas valem no reverse), para
    # não quebrar link, favorito ou código que ainda use o nome antigo.
    path('painel/', newsroom_views.dashboard, name='dashboard'),
    path('painel/', newsroom_views.dashboard, name='picker'),
    path('painel/espaco/', newsroom_views.switch_workspace, name='workspace'),
    path('sem-acesso/', panel_views.no_access, name='no_access'),
]
