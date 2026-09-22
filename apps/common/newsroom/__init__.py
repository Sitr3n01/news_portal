"""Painel administrativo unificado ("newsroom").

Uma única casca de navegação — sidebar, topbar e dashboard — servida da mesma
forma em três superfícies:

* a visão geral em ``/painel/`` (``views.dashboard``);
* as telas do Wagtail em ``/cms/`` (``templates/wagtailadmin/base.html``);
* as telas do Django admin/Unfold em ``/admin/`` (``templates/admin/nav_sidebar.html``
  e ``templates/unfold/helpers/header.html``).

Este pacote NÃO decide quem entra em qual área: isso continua sendo de
``apps.accounts.panels`` (porta). Aqui só se decide o que mostrar a quem já
passou pela porta (mobília), sempre delegando a checagem de permissão à mesma
política que a tela de destino aplica — assim o menu nunca promete uma tela que
a tela recusa. Ocultar um item não protege nada: cada view de destino continua
aplicando a própria checagem no backend.
"""
