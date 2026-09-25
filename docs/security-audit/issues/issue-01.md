Título: [Segurança] "Administrador Geral" consegue se promover a superusuário pelo admin
Labels sugeridas: security, severidade: alta

## Descrição
O projeto trata superusuário como uma fronteira separada: recursos guardados (códigos de
verificação, identidades Google, candidaturas, exportação de e-mails) são liberados só para
`is_superuser`, e o próprio formulário diz "Superusuário continua sendo uma escolha separada". No
servidor, porém, o `CustomUserAdmin` aceita `is_superuser`, `groups` e `user_permissions` de
qualquer conta com `accounts.change_customuser` — permissão que o grupo **Administrador Geral**
recebe junto com todas as de `auth.group`.

## Por que é explorável
Um Administrador Geral (não superusuário) envia `POST /admin/accounts/customuser/<próprio
id>/change/` com `is_superuser=on` e vira superusuário. Com a mesma permissão ele troca a senha de
um superusuário existente em `/admin/accounts/customuser/<id>/password/` (o `UserAdmin` só exige
permissão de change) e edita grupos no `/admin/auth/group/` e no `/cms/groups/`.

Confirmado com teste dinâmico (Django test client): o POST retornou 302 e `is_superuser` ficou
`True` no banco.

## Evidência
- `apps/accounts/admin.py:113-114`
```python
('Cargo e permissões', {
    'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
```
- `apps/accounts/admin_roles.py:56-66` (`GENERAL_ADMIN_APP_LABELS` inclui `'accounts'`) e `:126-138`
```python
def _general_admin_permissions():
    permissions = list(
        Permission.objects.filter(
            content_type__app_label__in=GENERAL_ADMIN_APP_LABELS,
        ).select_related('content_type')
    )
    permissions.extend(
        Permission.objects.filter(
            content_type__app_label='auth',
            content_type__model='group',
        ).select_related('content_type')
    )
    return permissions
```
- Fronteira só na interface: `apps/accounts/admin.py:116, 132`,
  `apps/common/newsroom/navigation.py:62-65`, `apps/common/admin_mixins.py:119-135`.

## Impacto
Escalada de privilégio de uma conta administrativa intermediária (ou de uma conta dessas
comprometida) para controle total: superusuário, tomada de contas de outros superusuários e acesso a
tudo o que hoje é "só superusuário".

## Sugestão de correção
```python
# apps/accounts/admin.py — CustomUserAdmin
SUPERUSER_ONLY_FIELDS = ('is_superuser', 'groups', 'user_permissions')

def get_readonly_fields(self, request, obj=None):
    fields = list(super().get_readonly_fields(request, obj))
    if not request.user.is_superuser:
        fields += [f for f in self.SUPERUSER_ONLY_FIELDS if f not in fields]
    return fields

def has_change_permission(self, request, obj=None):
    if obj is not None and obj.is_superuser and not request.user.is_superuser:
        return False  # cobre também a troca de senha (user_change_password)
    return super().has_change_permission(request, obj)

def has_delete_permission(self, request, obj=None):
    if obj is not None and obj.is_superuser and not request.user.is_superuser:
        return False
    return super().has_delete_permission(request, obj)
```
Em `apps/accounts/admin_roles.py`, dar ao Administrador Geral só `auth.view_group` (sem
add/change/delete), para que ele não consiga conceder permissões a si mesmo pelos grupos. A
sincronização cargo → grupo (`save_related`) continua funcionando.

## Critérios de aceite
- [ ] Administrador Geral não superusuário vê `is_superuser`, `groups` e `user_permissions` como
      somente leitura, e um POST forjado com `is_superuser=on` não altera o valor (teste
      automatizado).
- [ ] Não superusuário recebe 403 ao abrir, editar, trocar a senha ou excluir um superusuário.
- [ ] Administrador Geral não consegue criar/editar grupos em `/admin/auth/group/` nem em
      `/cms/groups/`.
- [ ] Testes de regressão em `apps/accounts/` cobrindo os três vetores; suíte completa verde.
