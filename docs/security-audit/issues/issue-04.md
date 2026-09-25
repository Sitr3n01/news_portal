Título: [Segurança] Download de currículos ignora a restrição a superusuário das Candidaturas
Labels sugeridas: security, severidade: média

## Descrição
Candidaturas são "recurso guardado": o `ApplicationAdmin` usa `SuperuserOnlyAdminMixin` e o menu só
as mostra a superusuário. A rota de download, porém, confere só `hiring.view_application`, permissão
que o grupo Administrador Geral recebe (`'hiring'` está em `GENERAL_ADMIN_APP_LABELS`).

## Por que é explorável
Um Administrador Geral (não superusuário) percorre `/hiring/application/1..N/resume/` (ID
sequencial) e baixa os currículos, enquanto `/admin/hiring/application/` responde 403.

Confirmado com teste dinâmico: changelist 403; download 200 com `X-Accel-Redirect:
/protected/hiring/resumes/...`.

## Evidência
- `apps/hiring/views.py:12-20`
```python
@staff_member_required
@permission_required('hiring.view_application', raise_exception=True)
def download_resume(request, application_id):
    ...
    application = get_object_or_404(Application, pk=application_id)
```
- `apps/hiring/admin.py:117-118`, `apps/common/newsroom/navigation.py:238-239`,
  `apps/accounts/admin_roles.py:56-66`

## Impacto
Exposição de dados pessoais de candidatos (currículos) a um papel que a interface declara sem
acesso.

## Sugestão de correção
Reusar a mesma regra do admin, para as duas nunca divergirem:
```python
from django.contrib import admin
from django.core.exceptions import PermissionDenied

@staff_member_required
def download_resume(request, application_id):
    if not admin.site.get_model_admin(Application).has_view_permission(request):
        raise PermissionDenied
    application = get_object_or_404(Application, pk=application_id)
```
Alternativa complementar: retirar `'hiring'` de `GENERAL_ADMIN_APP_LABELS`.

## Critérios de aceite
- [ ] Administrador Geral não superusuário recebe 403 em `/hiring/application/<id>/resume/`.
- [ ] Superusuário continua baixando o currículo.
- [ ] Teste de regressão em `apps/hiring/tests.py`.
