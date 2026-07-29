from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .emails import send_verification_code_email
from .forms import CustomUserCreationForm, ProfileForm
from .models import VerificationCode
from .verification import issue_code

# A recuperação de senha mudou de link para código e vive em code_views.py.
# `CustomPasswordResetView` foi removida junto com os baldes de rate limit que
# só ela usava: o rate limit equivalente agora é `verification.throttle`, e
# manter aqui uma view que ainda enviaria link por e-mail, ao lado do fluxo
# novo, seria fonte garantida de confusão. A proteção contra host header
# poisoning que ela tinha (`domain_override`) deixou de ser necessária pelo
# motivo mais direto possível: o e-mail de código não carrega URL nenhuma.


class CustomLoginView(LoginView):
    """Login do portal público (leitores: comentar, curtir, salvar).

    O acesso da equipe aos painéis fica em ``panel:login`` (/entrar/), que
    apresenta a escolha entre Publicação de matérias e Administração do sistema.
    """

    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


def register_view(request):
    if request.user.is_authenticated:
        return redirect('news:list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request=request)
        if form.is_valid():
            user = form.save()

            # Opt-in de newsletter durante o cadastro (LGPD: ação explícita do usuário)
            if form.cleaned_data.get('subscribe_newsletter') and user.email:
                from apps.news.models import NewsletterSubscription
                site = get_current_site(request)
                NewsletterSubscription.objects.get_or_create(
                    email=user.email,
                    site=site,
                    defaults={'is_active': True},
                )

            # Confirmação de e-mail (Fase 3, bloqueio suave): emite e envia o
            # código ANTES do login, para a tela pós-cadastro já ter algo a
            # confirmar. Se issue_code recusar (rate limit — improvável para
            # quem acabou de nascer, mas a função é genérica e compartilhada)
            # ou o envio falhar (SMTP fora do ar), o cadastro NÃO é abortado:
            # a conta já existe e a pessoa já vai entrar; a tela de
            # confirmação (accounts:verify_email) sempre oferece "Reenviar
            # código" para tentar de novo depois.
            code = issue_code(user, VerificationCode.Purpose.EMAIL_VERIFICATION, request=request)
            if code is not None:
                send_verification_code_email(user, code, request=request)

            # backend explícito: o projeto tem múltiplos AUTHENTICATION_BACKENDS
            # (axes + ModelBackend, em base.py), então login() não consegue inferir o
            # backend de um usuário recém-criado (não veio de authenticate()). Sem
            # isto, login() levanta ValueError e o cadastro retorna HTTP 500.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Conta criada! Confirme seu e-mail com o código que enviamos.')
            return redirect('accounts:verify_email')
    else:
        initial = {}
        if email := request.GET.get('email'):
            initial['email'] = email
        form = CustomUserCreationForm(initial=initial, request=request)

    return render(request, 'accounts/register.html', {'form': form})


@login_required
@require_POST
def delete_account(request):
    """Deleta a conta do usuario apos confirmacao de senha."""
    password = request.POST.get('password', '')
    user = request.user

    if not user.check_password(password):
        messages.error(request, 'Senha incorreta. Tente novamente.')
        return redirect('news:user_dashboard')

    # Faz logout antes de deletar
    logout(request)
    user.delete()

    messages.success(request, 'Sua conta foi excluída com sucesso.')
    return redirect('news:list')


@login_required
@require_POST
def update_profile(request):
    """Atualiza a foto de perfil do usuário (envio ou remoção).

    Envio: valida via ProfileForm (validador do modelo) e, ao trocar, apaga o
    arquivo anterior do disco para não deixar órfãos no volume de mídia.
    """
    user = request.user
    dashboard = f"{reverse('news:user_dashboard')}?tab=settings"

    # Remoção explícita: apaga o arquivo e limpa o campo.
    if request.POST.get('action') == 'remove':
        if user.avatar:
            user.avatar.delete(save=True)
            messages.success(request, 'Foto de perfil removida.')
        return redirect(dashboard)

    if 'avatar' not in request.FILES:
        messages.error(request, 'Selecione uma imagem para enviar.')
        return redirect(dashboard)

    old_file = user.avatar or None
    old_name = old_file.name if old_file else ''

    form = ProfileForm(request.POST, request.FILES, instance=user)
    if form.is_valid():
        form.save()
        # Higiene de disco: remove a foto anterior se o arquivo mudou.
        if old_name and user.avatar.name != old_name:
            old_file.storage.delete(old_name)
        messages.success(request, 'Foto de perfil atualizada!')
    else:
        errors = form.errors.get('avatar')
        messages.error(request, errors[0] if errors else 'Não foi possível atualizar a foto.')

    return redirect(dashboard)


@login_required
@require_POST
def toggle_newsletter(request):
    """Alterna a inscricao do usuario na newsletter (inscreve/cancela)."""
    from apps.news.models import NewsletterSubscription

    site = get_current_site(request)
    email = request.user.email

    if not email:
        messages.error(request, 'Adicione um e-mail à sua conta para se inscrever na newsletter.')
        return redirect('news:user_dashboard')

    action = request.POST.get('action', 'unsubscribe')

    if action == 'subscribe':
        obj, created = NewsletterSubscription.objects.get_or_create(
            email=email,
            site=site,
            defaults={'is_active': True},
        )
        if not created and not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=['is_active'])
        messages.success(request, 'Inscrição na newsletter ativada! Você receberá nossas novidades por e-mail.')
    else:
        NewsletterSubscription.objects.filter(
            email=email,
            site=site,
            is_active=True,
        ).update(is_active=False)
        messages.success(request, 'Inscrição na newsletter cancelada com sucesso.')

    return redirect('news:user_dashboard')

