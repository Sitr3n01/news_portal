"""Registra SiteExtension como Wagtail Snippet — edição consolidada no /cms/ —
e carrega a casca do painel unificado (apps/common/newsroom) em todo o Wagtail.

Mantém o FK existente para ``django.contrib.sites.Site``, sem envolver
``wagtail.models.Site`` ou ``wagtail.contrib.settings`` em nenhum momento.
Sem RevisionMixin / DraftStateMixin / WorkflowMixin — mesma simplicidade
que Category/Tag.
"""

from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.common.models import SiteExtension


class SiteExtensionSnippetViewSet(SnippetViewSet):
    model = SiteExtension
    icon = 'cog'
    menu_label = 'Configurações do Site'
    menu_name = 'site-extension'
    menu_order = 9500
    add_to_admin_menu = True
    list_display = ('site', 'primary_email', 'newsletter_from_email')
    search_fields = ('site__name', 'primary_email')

    panels = [
        FieldPanel(
            'site',
            help_text='Não altere depois de criado — é 1-para-1 com o portal.',
        ),
        MultiFieldPanel(
            [
                FieldPanel('newsletter_from_email'),
                FieldPanel('newsletter_from_name'),
            ],
            heading='Newsletter — e-mail remetente',
            help_text=(
                'E-mail e nome que aparecem como remetente das newsletters deste portal. '
                'O servidor SMTP (host, usuário e senha) continua no .env.prod.'
            ),
        ),
        MultiFieldPanel(
            [
                FieldPanel('tagline'),
                FieldPanel('tagline_en'),
                FieldPanel('logo'),
                FieldPanel('favicon'),
            ],
            heading='Identidade visual',
        ),
        MultiFieldPanel(
            [
                FieldPanel('primary_email'),
                FieldPanel('phone_number'),
                FieldPanel('address'),
            ],
            heading='Contato',
        ),
        MultiFieldPanel(
            [
                FieldPanel('google_analytics_id'),
                FieldPanel('facebook_url'),
                FieldPanel('instagram_url'),
                FieldPanel('tiktok_url'),
                FieldPanel('youtube_url'),
            ],
            heading='Analytics e redes sociais',
        ),
        MultiFieldPanel(
            [
                FieldPanel('social_section_enabled'),
                FieldPanel('social_show_instagram'),
                FieldPanel('social_show_tiktok'),
                FieldPanel('social_section_title'),
                FieldPanel('social_section_title_en'),
                FieldPanel('social_section_subtitle'),
                FieldPanel('social_section_subtitle_en'),
            ],
            heading='Seção de redes na home',
        ),
    ]


register_snippet(SiteExtensionSnippetViewSet)


# ── Painel unificado: design system e comportamento da casca ────────────────
# Hooks oficiais do Wagtail para CSS/JS globais do admin. O CSS entra depois
# do core.css do Wagtail, então os tokens --w-color-* definidos aqui prevalecem.


@hooks.register('insert_global_admin_css')
def newsroom_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}"><link rel="stylesheet" href="{}">',
        static('newsroom/css/newsroom.css'),
        static('newsroom/css/newsroom-wagtail.css'),
    )


@hooks.register('insert_global_admin_js')
def newsroom_admin_js():
    return format_html('<script src="{}" defer></script>', static('newsroom/js/newsroom.js'))


# Só nos formulários de criação e edição: ajusta o arrastar dos blocos do
# StreamField (pega pela barra de título, alça no celular e posição correta
# depois de excluir um bloco). Detalhes no cabeçalho do próprio arquivo.
@hooks.register('insert_editor_js')
def newsroom_streamfield_js():
    return format_html('<script src="{}" defer></script>', static('newsroom/js/newsroom-streamfield.js'))
