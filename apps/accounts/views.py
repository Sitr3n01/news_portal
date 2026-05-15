from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import CustomUserCreationForm


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset/password_reset_form.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    email_template_name = 'accounts/password_reset/password_reset_email.html'

    def form_valid(self, form):
        # 1. Protection contra Mailbombing (Rate Limiting)
        ip = self.request.META.get('HTTP_X_FORWARDED_FOR', self.request.META.get('REMOTE_ADDR', ''))
        ip = ip.split(',')[0].strip() if ip else 'unknown_ip'
        email = form.cleaned_data.get('email', '')

        cache_key = f'pwd_reset_limit_{ip}_{email}'
        if cache.get(cache_key):
            # Silently drops the email dispatch to prevent inbox DoS, but returns success to avoid tipping off attacker
            return HttpResponseRedirect(self.get_success_url())

        cache.set(cache_key, True, timeout=900)  # Blocks repeat requests for 15 minutes

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

            login(request, user)
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

