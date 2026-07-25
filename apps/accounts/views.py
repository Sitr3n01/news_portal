import hashlib

from axes.helpers import get_client_ip_address
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .forms import CustomUserCreationForm, ProfileForm

# Janela e teto do rate limit de recuperação de senha.
RESET_THROTTLE_WINDOW = 900  # 15 minutos
RESET_IP_LIMIT = 10          # pedidos por IP dentro da janela


def _hash_key(*parts):
    """Deriva uma chave de cache opaca e de tamanho fixo a partir de dados sensíveis."""
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()


class CustomLoginView(LoginView):
    """Login do portal público (leitores: comentar, curtir, salvar).

    O acesso da equipe aos painéis fica em ``panel:login`` (/entrar/), que
    apresenta a escolha entre Publicação de matérias e Administração do sistema.
    """

    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset/password_reset_form.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    email_template_name = 'accounts/password_reset/password_reset_email.html'
    subject_template_name = 'accounts/password_reset/password_reset_subject.txt'

    def form_valid(self, form):
        # 1. Proteção contra mailbombing (rate limiting), em dois níveis.
        #
        # O IP vem do helper do axes, que respeita AXES_IPWARE_PROXY_COUNT e
        # AXES_IPWARE_META_PRECEDENCE_ORDER (base.py) — não dá para confiar num
        # parse manual de X-Forwarded-For, que é forjável quando a contagem de
        # proxies não é levada em conta.
        ip = get_client_ip_address(self.request) or 'unknown_ip'
        email = (form.cleaned_data.get('email') or '').strip().lower()

        # Balde por (IP, e-mail): impede repetir o pedido para o mesmo destino.
        # A chave é um hash porque a chave crua carregava e-mail e IP em texto
        # puro para dentro do backend de cache (que hoje é uma tabela no banco).
        # Normalizar o e-mail evita que A@x.com e a@x.com virem baldes distintos.
        pair_key = f'pwd_reset:pair:{_hash_key(ip, email)}'
        # Balde só por IP: sem ele, uma única origem podia disparar e-mails para
        # infinitos endereços distintos, já que cada par tinha o próprio balde.
        ip_key = f'pwd_reset:ip:{_hash_key(ip)}'

        if cache.get(pair_key) or cache.get_or_set(ip_key, 0, RESET_THROTTLE_WINDOW) >= RESET_IP_LIMIT:
            # Descarta o envio em silêncio para não transformar o formulário em
            # arma de DoS de caixa de entrada, mas devolve sucesso para não
            # revelar ao atacante que houve bloqueio.
            return HttpResponseRedirect(self.get_success_url())

        cache.set(pair_key, True, timeout=RESET_THROTTLE_WINDOW)
        try:
            cache.incr(ip_key)
        except ValueError:
            # A chave expirou entre o get_or_set e o incr — recria o balde.
            cache.set(ip_key, 1, timeout=RESET_THROTTLE_WINDOW)

        # 2. Protection contra Host Header Poisoning
        site = get_current_site(self.request)
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
            'domain_override': site.domain,  # Forces DB Domain definition, ignoring HTTP spoofing headers
        }
        form.save(**opts)
        return HttpResponseRedirect(self.get_success_url())


def register_view(request):
    if request.user.is_authenticated:
        return redirect('news:list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
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

            # backend explícito: o projeto tem múltiplos AUTHENTICATION_BACKENDS
            # (axes + ModelBackend, em base.py), então login() não consegue inferir o
            # backend de um usuário recém-criado (não veio de authenticate()). Sem
            # isto, login() levanta ValueError e o cadastro retorna HTTP 500.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('news:list')
    else:
        initial = {}
        if email := request.GET.get('email'):
            initial['email'] = email
        form = CustomUserCreationForm(initial=initial)

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

