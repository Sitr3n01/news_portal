from django import forms
from django.contrib import admin, messages
from django.contrib.sites.models import Site
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.utils.text import Truncator
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import SocialAccount, SocialPost


class SocialAccountAdminForm(forms.ModelForm):
    """Trata os tokens como campos password-like: nunca reexibe o valor no DOM
    (render_value=False) e, se enviado em branco, mantém o token já salvo."""

    access_token = forms.CharField(
        label='Token de acesso', required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Sensível. Deixe em branco para manter o token atual. '
                  'Prefira variável de ambiente; nunca compartilhe nem versione.',
    )
    refresh_token = forms.CharField(
        label='Token de atualização', required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Sensível. Opcional. Deixe em branco para manter o valor atual.',
    )

    class Meta:
        model = SocialAccount
        fields = '__all__'

    def clean_access_token(self):
        value = self.cleaned_data.get('access_token')
        if not value and self.instance and self.instance.pk:
            return self.instance.access_token
        return value

    def clean_refresh_token(self):
        value = self.cleaned_data.get('refresh_token')
        if not value and self.instance and self.instance.pk:
            return self.instance.refresh_token
        return value


@admin.register(SocialAccount)
class SocialAccountAdmin(AdminUXMixin, ModelAdmin):
    form = SocialAccountAdminForm
    list_display = ['display_name', 'platform', 'username', 'is_active', 'last_sync_status', 'last_sync_at']
    list_filter = ['platform', 'is_active', 'last_sync_status', 'site']
    list_filter_submit = True
    search_fields = ['display_name', 'username']
    readonly_fields = ['last_sync_status', 'last_sync_at', 'last_sync_error', 'created_at', 'updated_at']
    actions = ['activate_accounts', 'deactivate_accounts']
    ux_list_title = 'Contas de redes sociais'
    ux_list_description = 'Cadastre os perfis oficiais de Instagram e TikTok e acompanhe o status da sincronização.'
    ux_list_icon = 'share'
    ux_empty_message = 'Nenhuma conta cadastrada. Adicione o Instagram e o TikTok oficiais para alimentar a home.'
    ux_form_title = 'Conta de rede social'
    ux_form_description = 'Os links públicos alimentam os botões da home. As credenciais de API são opcionais e ficam recolhidas.'
    ux_form_icon = 'share'
    ux_form_steps = [
        'Escolha o site e a plataforma e dê um nome de exibição.',
        'Informe o usuário e o link público do perfil.',
        'As credenciais de API são opcionais — só preencha ao conectar a API oficial.',
    ]
    fieldsets = [
        ('Identidade', {
            'fields': ('site', 'platform', 'display_name', 'username'),
        }),
        ('Link oficial', {
            'fields': ('profile_url',),
            'description': 'Endereço público do perfil — usado nos botões da seção de redes.',
        }),
        ('Credenciais de API (sensível)', {
            'fields': ('external_user_id', 'access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',),
            'description': (
                'Opcional e apenas para a sincronização automática com as APIs oficiais. '
                'Tokens são sensíveis: prefira variáveis de ambiente, nunca compartilhe '
                'nem versione. Deixe os campos de token em branco para manter os valores atuais.'
            ),
        }),
        ('Status da sincronização', {
            'fields': ('is_active', 'last_sync_status', 'last_sync_at', 'last_sync_error'),
            'description': 'Os campos de status são atualizados automaticamente pelo comando sync_social_posts.',
        }),
    ]

    @admin.action(description='Ativar contas selecionadas')
    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} conta(s) ativada(s).')

    @admin.action(description='Desativar contas selecionadas')
    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} conta(s) desativada(s).')


@admin.register(SocialPost)
class SocialPostAdmin(AdminUXMixin, ModelAdmin):
    # Toggles de exibição da seção (recurso/Instagram/TikTok) ficam no topo desta tela.
    list_before_template = 'admin/social/socialpost_change_list_before.html'
    list_display = ['thumbnail_preview', 'caption_short', 'platform', 'account', 'published_at', 'is_visible', 'is_manual']
    list_display_links = ['caption_short']
    list_filter = ['platform', 'is_visible', 'is_manual', 'account', 'published_at']
    list_filter_submit = True
    search_fields = ['caption', 'account__username', 'permalink']
    date_hierarchy = 'published_at'
    autocomplete_fields = ['account']
    readonly_fields = ['platform', 'thumbnail_preview', 'sync_payload', 'created_at', 'updated_at']
    actions = ['make_visible', 'make_hidden']
    ux_list_title = 'Posts de redes sociais'
    ux_list_description = 'Cadastre posts manualmente (fallback) ou revise os que vieram da sincronização. Só os visíveis aparecem na home.'
    ux_list_icon = 'dynamic_feed'
    ux_empty_message = 'Nenhum post cadastrado. Adicione um post manual ou rode a sincronização para popular a home.'
    ux_form_title = 'Post de rede social'
    ux_form_description = 'Para posts manuais: informe o link, a legenda, a data e envie uma imagem (ou cole a URL da miniatura).'
    ux_form_icon = 'dynamic_feed'
    ux_form_steps = [
        'Escolha a conta — a plataforma é definida automaticamente.',
        'Cole o link público do post e a data de publicação.',
        'Envie uma imagem de miniatura (ou informe a URL) e mantenha "visível" marcado.',
    ]
    fieldsets = [
        ('Publicação', {
            'fields': ('account', 'platform', 'permalink', 'published_at', 'external_id'),
            'description': 'A plataforma acompanha a conta automaticamente. Em posts manuais o ID é gerado sozinho.',
        }),
        ('Conteúdo', {
            'fields': ('caption', 'media_type', 'thumbnail_image', 'thumbnail_preview', 'thumbnail_url', 'media_url'),
            'description': 'A imagem enviada tem prioridade sobre a URL da miniatura. Sem nenhuma, o card mostra um placeholder.',
        }),
        ('Visibilidade', {
            'fields': ('is_visible', 'is_manual'),
        }),
        ('Técnico', {
            'fields': ('sync_payload', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Resumo do retorno da API (sem tokens) e datas de controle.',
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account')

    @admin.display(description='Miniatura')
    def thumbnail_preview(self, obj):
        url = obj.thumbnail
        if url:
            return format_html(
                '<img src="{}" loading="lazy" style="height:48px;width:48px;object-fit:cover;border-radius:8px;">',
                url,
            )
        return '—'

    @admin.display(description='Legenda')
    def caption_short(self, obj):
        text = (obj.caption or '').strip()
        if text:
            return Truncator(text).chars(60)
        return f'(sem legenda) · {obj.external_id or obj.pk}'

    @admin.action(description='Exibir posts selecionados no site')
    def make_visible(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f'{updated} post(s) agora visível(is) na home.')

    @admin.action(description='Ocultar posts selecionados do site')
    def make_hidden(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f'{updated} post(s) ocultado(s) da home.')

    # ── Toggles de exibição da seção (no topo da lista de posts) ──────────────
    def _current_feed_settings(self):
        """SiteExtension do site atual — guarda os toggles da seção da home."""
        from apps.common.models import SiteExtension
        ext, _ = SiteExtension.objects.get_or_create(site=Site.objects.get_current())
        return ext

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'exibicao-na-home/',
                self.admin_site.admin_view(self.toggle_feed_view),
                name='social_socialpost_toggle_feed',
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['feed_settings'] = self._current_feed_settings()
        return super().changelist_view(request, extra_context=extra_context)

    def toggle_feed_view(self, request):
        redirect_url = redirect('admin:social_socialpost_changelist')
        if request.method != 'POST':
            return redirect_url
        if not request.user.has_perm('common.change_siteextension'):
            messages.error(request, 'Você não tem permissão para alterar a exibição da seção.')
            return redirect_url
        ext = self._current_feed_settings()
        ext.social_section_enabled = 'enabled' in request.POST
        ext.social_show_instagram = 'show_instagram' in request.POST
        ext.social_show_tiktok = 'show_tiktok' in request.POST
        ext.save(update_fields=['social_section_enabled', 'social_show_instagram', 'social_show_tiktok'])
        messages.success(request, 'Exibição da seção de redes na home atualizada.')
        return redirect_url
