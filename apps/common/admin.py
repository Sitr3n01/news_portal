from django.contrib import admin
from django.contrib.sites.models import Site

# O Sites Framework permanece ativo (contexto multi-site, domínio de e-mail), mas
# não tem mais página no admin: domínios raramente mudam e a tela só confundia
# usuários. Ajustes de domínio, quando necessários, são feitos via shell/migração.
try:
    admin.site.unregister(Site)
except admin.sites.NotRegistered:
    pass
