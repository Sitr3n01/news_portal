"""Rotas do acesso administrativo unificado.

Montadas na raiz (cada padrão carrega o caminho completo) para que fiquem
legíveis em português — /entrar/, /sair/ — mas continuem morando num módulo de
aplicação. Ver a ordem exigida em config/urls.py.
"""

from django.urls import path

from apps.accounts import panel_views

app_name = 'panel'

urlpatterns = [
    path('entrar/', panel_views.PanelLoginView.as_view(), name='login'),
    path('sair/', panel_views.panel_logout, name='logout'),
    path('painel/', panel_views.panel_picker, name='picker'),
    path('sem-acesso/', panel_views.no_access, name='no_access'),
]
