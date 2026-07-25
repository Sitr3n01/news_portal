from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.shortcuts import render

from apps.common.admin_nav import (
    MANAGEMENT_PERMISSIONS,
    SCHOOL_PERMISSIONS,
)
from apps.common.admin_nav import admin_url as _admin_url
from apps.common.admin_nav import can as _can
from apps.common.admin_nav import can_any as _can_any
from apps.common.admin_nav import get_email_status as _get_email_status


def _external_url(path):
    return path


def _action(user, title, icon, route_name, permission, query=None, args=None, kind='secondary'):
    if not _can(user, permission):
        return None
    return {
        'title': title,
        'icon': icon,
        'url': _admin_url(route_name, query=query, args=args),
        'kind': kind,
    }


def _public_action(title, icon, url, kind='secondary'):
    return {
        'title': title,
        'icon': icon,
        'url': _external_url(url),
        'kind': kind,
    }


def _visible(items):
    return [item for item in items if item]


def _metric(title, value, icon, tone='neutral', hint=''):
    return {
        'title': title,
        'value': value,
        'icon': icon,
        'tone': tone,
        'hint': hint,
    }


def _check(title, done, hint, url='', icon='task_alt'):
    return {
        'title': title,
        'done': done,
        'hint': hint,
        'url': url,
        'icon': icon,
        'tone': 'success' if done else 'warning',
    }


def _resource_group(title, description, links):
    visible_links = _visible(links)
    if not visible_links:
        return None
    return {
        'title': title,
        'description': description,
        'links': visible_links,
    }


def _workflow(title, icon, description, status, tone, actions):
    return {
        'title': title,
        'icon': icon,
        'description': description,
        'status': status,
        'tone': tone,
        'actions': _visible(actions),
    }


def _recent_card(title, icon, empty, items):
    return {
        'title': title,
        'icon': icon,
        'empty': empty,
        'items': items,
    }


def _guide_response(request, guide):
    context = admin.site.each_context(request)
    context.update({
        'title': guide['title'],
        'content_title': guide['title'],
        'guide': guide,
    })
    return render(request, 'admin/guides/guide.html', context)


def school_guide(request):
    from apps.contact.models import ContactInquiry
    from apps.school.models import Page, SchoolFeature, SchoolHomeConfig, Testimonial

    user = request.user
    has_access = _can_any(user, SCHOOL_PERMISSIONS)
    home_configs = SchoolHomeConfig.objects.filter(is_active=True).count()
    published_courses = Page.objects.filter(slug='cursos', is_published=True).count()
    active_features = SchoolFeature.objects.filter(
        is_active=True,
        placement__in=[
            SchoolFeature.Placement.TRUST,
            SchoolFeature.Placement.LIFE,
        ],
    ).count()
    featured_testimonials = Testimonial.objects.filter(is_featured=True).count()
    unread_messages = ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW).count()

    recent_messages = [
        {
            'title': message.name,
            'meta': message.get_subject_display(),
            'url': _admin_url('admin:contact_contactinquiry_change', args=[message.pk]),
            'status': message.get_status_display(),
        }
        for message in ContactInquiry.objects.order_by('-created_at')[:5]
    ] if _can(user, 'contact.view_contactinquiry') else []

    guide = {
        'area': 'school',
        'has_access': has_access,
        'eyebrow': 'Komuniki',
        'title': 'Operação Komuniki',
        'subtitle': 'Gerencie a presença pública atual: home, cursos, blocos visuais, depoimentos e mensagens.',
        'icon': 'school',
        'primary_actions': _visible([
            _action(user, 'Editar Home Komuniki', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig', kind='primary'),
            _public_action('Ver Komuniki', 'open_in_new', '/'),
            _action(user, 'Mensagens novas', 'mail', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry', query={'status__exact': ContactInquiry.Status.NEW}),
        ]),
        'metrics': [
            _metric('Home ativa', home_configs, 'home', 'success' if home_configs else 'warning', 'Configuração principal'),
            _metric('Página Cursos', published_courses, 'article', 'primary' if published_courses else 'warning', 'Link público da navegação'),
            _metric('Blocos ativos', active_features, 'auto_awesome', 'primary' if active_features else 'neutral', 'Home Komuniki'),
            _metric('Mensagens novas', unread_messages, 'priority_high', 'warning' if unread_messages else 'neutral', 'Contato'),
        ],
        'workflows': [
            _workflow(
                'Configurar Home Komuniki',
                'home',
                'Comece pela home, depois revise blocos e depoimentos que aparecem na página inicial.',
                'Pronto' if home_configs and active_features else 'Atenção',
                'success' if home_configs and active_features else 'warning',
                [
                    _action(user, 'Home Komuniki', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig', kind='primary'),
                    _action(user, 'Blocos da Home', 'auto_awesome', 'admin:school_schoolfeature_changelist', 'school.view_schoolfeature'),
                    _action(user, 'Depoimentos', 'format_quote', 'admin:school_testimonial_changelist', 'school.view_testimonial'),
                ],
            ),
            _workflow(
                'Manter Página Cursos',
                'article',
                'A página Cursos precisa ficar publicada para a navegação pública continuar funcionando.',
                'Publicada' if published_courses else 'Revisar',
                'success' if published_courses else 'warning',
                [
                    _action(user, 'Página Cursos', 'article', 'admin:school_page_changelist', 'school.view_page', kind='primary'),
                    _public_action('Ver cursos', 'open_in_new', '/cursos/'),
                ],
            ),
            _workflow(
                'Atender interessados',
                'contact_mail',
                'Responda mensagens novas primeiro e arquive o que já foi tratado.',
                'Requer resposta' if unread_messages else 'Tudo em dia',
                'warning' if unread_messages else 'success',
                [
                    _action(
                        user, 'Novas mensagens', 'mail',
                        'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry',
                        query={'status__exact': ContactInquiry.Status.NEW}, kind='primary',
                    ),
                    _action(user, 'Todas as mensagens', 'inbox', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry'),
                ],
            ),
        ],
        'readiness': [
            _check(
                'Home Komuniki ativa',
                bool(home_configs),
                'Configure a página inicial antes de divulgar o site.',
                _admin_url('admin:school_schoolhomeconfig_changelist') if _can(user, 'school.view_schoolhomeconfig') else '',
            ),
            _check(
                'Página Cursos publicada',
                published_courses > 0,
                'Mantenha a página Cursos ativa para o link público funcionar.',
                _admin_url('admin:school_page_changelist') if _can(user, 'school.view_page') else '',
            ),
            _check(
                'Blocos da Home ativos',
                active_features > 0,
                'Cadastre blocos exibidos na home.',
                _admin_url('admin:school_schoolfeature_changelist') if _can(user, 'school.view_schoolfeature') else '',
            ),
            _check(
                'Depoimentos destacados',
                featured_testimonials > 0,
                'Use relatos para reforçar confiança na Komuniki.',
                _admin_url('admin:school_testimonial_changelist') if _can(user, 'school.view_testimonial') else '',
            ),
        ],
        'resources': _visible([
            _resource_group('Presença Komuniki', 'Textos e blocos usados nas páginas públicas atuais.', [
                _action(user, 'Home Komuniki', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig'),
                _action(user, 'Página Cursos', 'article', 'admin:school_page_changelist', 'school.view_page'),
                _action(user, 'Blocos da Home', 'auto_awesome', 'admin:school_schoolfeature_changelist', 'school.view_schoolfeature'),
            ]),
            _resource_group('Relacionamento', 'Relatos e mensagens recebidas pelo site.', [
                _action(user, 'Depoimentos', 'format_quote', 'admin:school_testimonial_changelist', 'school.view_testimonial'),
                _action(user, 'Mensagens', 'contact_mail', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry'),
            ]),
        ]),
        'recent_cards': _visible([
            _recent_card('Mensagens recentes', 'mail', 'Nenhuma mensagem recente', recent_messages) if _can(user, 'contact.view_contactinquiry') else None,
        ]),
        'empty_message': 'Você ainda não tem permissões para operar a Komuniki.',
    }
    return _guide_response(request, guide)


def management_guide(request):
    from apps.common.models import SiteExtension
    from apps.media_library.models import MediaFile, MediaFolder
    from apps.news.models import NewsletterDelivery

    user = request.user
    user_model = get_user_model()
    has_access = _can_any(user, MANAGEMENT_PERMISSIONS)
    staff_users = user_model.objects.filter(is_staff=True).count()
    active_users = user_model.objects.filter(is_active=True).count()
    groups = Group.objects.count()
    sites = Site.objects.count()
    configured_sites = SiteExtension.objects.exclude(primary_email='').count()
    sender_sites = SiteExtension.objects.exclude(newsletter_from_email='').count()
    media_files = MediaFile.objects.count()
    media_folders = MediaFolder.objects.count()
    failed_deliveries = NewsletterDelivery.objects.filter(status=NewsletterDelivery.Status.FAILED).count()
    email_status = _get_email_status()
    email_ready = email_status['smtp_configured'] and sender_sites > 0

    guide = {
        'area': 'management',
        'has_access': has_access,
        'eyebrow': 'Gerenciamento',
        'title': 'Operação e Configurações',
        'subtitle': 'Administre pessoas, permissões, sites, mídia e saúde técnica sem misturar tarefas editoriais ou escolares.',
        'icon': 'admin_panel_settings',
        'primary_actions': _visible([
            _action(user, 'Usuários', 'manage_accounts', 'admin:accounts_customuser_changelist', 'accounts.view_customuser', kind='primary'),
            _action(user, 'Configurações dos sites', 'settings', 'wagtailsnippets_common_siteextension:list', 'common.view_siteextension'),
            _action(user, 'Biblioteca de mídia', 'perm_media', 'admin:media_library_mediafile_changelist', 'media_library.view_mediafile'),
        ]),
        'metrics': [
            _metric('Usuários ativos', active_users, 'person', 'primary', f'{staff_users} com acesso ao admin'),
            _metric('Perfis administrativos', groups, 'badge', 'success' if groups else 'warning', 'Grupos de acesso'),
            _metric('Sites cadastrados', sites, 'language', 'primary', 'Django Sites'),
            _metric('Saúde de e-mail', 'Pronto' if email_ready else 'Atenção', 'mail', 'success' if email_ready else 'warning', 'SMTP e remetente'),
        ],
        'workflows': [
            _workflow(
                'Pessoas e permissões',
                'manage_accounts',
                'Crie usuários reais e atribua grupos por responsabilidade, evitando superusuário para tarefas do dia a dia.',
                'Revisar perfis' if not groups else 'Perfis disponíveis',
                'warning' if not groups else 'success',
                [
                    _action(user, 'Usuários', 'manage_accounts', 'admin:accounts_customuser_changelist', 'accounts.view_customuser', kind='primary'),
                    _action(user, 'Grupos de permissões', 'badge', 'admin:auth_group_changelist', 'auth.view_group'),
                ],
            ),
            _workflow(
                'Identidade dos sites',
                'settings',
                'Revise contato, marca, remetente de newsletter e dados públicos de cada site.',
                'Completar dados' if configured_sites < sites else 'Configurado',
                'warning' if configured_sites < sites else 'success',
                [
                    _action(user, 'Configurações dos sites', 'settings', 'wagtailsnippets_common_siteextension:list', 'common.view_siteextension', kind='primary'),
                ],
            ),
            _workflow(
                'Envio de e-mails',
                'outgoing_mail',
                'Acompanhe SMTP, remetentes por site e falhas de newsletter sem expor detalhes técnicos para toda equipe.',
                'Atenção' if not email_ready or failed_deliveries else 'Tudo saudável',
                'danger' if failed_deliveries else ('warning' if not email_ready else 'success'),
                [
                    _action(user, 'Configurar remetentes', 'settings_account_box', 'wagtailsnippets_common_siteextension:list', 'common.view_siteextension', kind='primary'),
                    _action(
                        user, 'Falhas de newsletter', 'error',
                        'admin:news_newsletterdelivery_changelist', 'news.view_newsletterdelivery',
                        query={'status__exact': NewsletterDelivery.Status.FAILED},
                    ),
                ],
            ),
            _workflow(
                'Biblioteca de mídia',
                'perm_media',
                'Organize imagens e documentos usados nos portais com título, pasta e texto alternativo.',
                'Organizada' if media_folders else 'Criar pastas',
                'success' if media_folders else 'warning',
                [
                    _action(user, 'Arquivos de mídia', 'perm_media', 'admin:media_library_mediafile_changelist', 'media_library.view_mediafile', kind='primary'),
                    _action(user, 'Pastas', 'folder', 'admin:media_library_mediafolder_changelist', 'media_library.view_mediafolder'),
                ],
            ),
        ],
        'readiness': [
            _check('Grupos administrativos criados', groups >= 4, 'Perfis reduzem risco de permissões excessivas.', _admin_url('admin:auth_group_changelist') if _can(user, 'auth.view_group') else ''),
            _check('Sites cadastrados', sites > 0, 'O Sites Framework define contexto dos portais.', ''),
            _check(
                'Contatos dos sites configurados',
                configured_sites >= sites and sites > 0,
                'Preencha e-mail, telefone e identidade pública.',
                _admin_url('wagtailsnippets_common_siteextension:list') if _can(user, 'common.view_siteextension') else '',
            ),
            _check(
                'Remetente da newsletter configurado',
                sender_sites > 0,
                'Cada site precisa de remetente amigável para envios.',
                _admin_url('wagtailsnippets_common_siteextension:list') if _can(user, 'common.view_siteextension') else '',
            ),
            _check('Servidor de e-mail pronto', email_status['smtp_configured'], 'Configuração SMTP completa libera envios reais.', ''),
        ],
        'resources': _visible([
            _resource_group('Acessos', 'Usuários e perfis administrativos.', [
                _action(user, 'Usuários', 'manage_accounts', 'admin:accounts_customuser_changelist', 'accounts.view_customuser'),
                _action(user, 'Grupos de permissões', 'badge', 'admin:auth_group_changelist', 'auth.view_group'),
            ]),
            _resource_group('Sites e configuração', 'Identidade e remetentes dos portais.', [
                _action(user, 'Configurações dos sites', 'settings', 'wagtailsnippets_common_siteextension:list', 'common.view_siteextension'),
            ]),
            _resource_group('Mídia compartilhada', 'Arquivos reutilizáveis em páginas e artigos.', [
                _action(user, 'Arquivos', 'perm_media', 'admin:media_library_mediafile_changelist', 'media_library.view_mediafile'),
                _action(user, 'Pastas', 'folder', 'admin:media_library_mediafolder_changelist', 'media_library.view_mediafolder'),
            ]),
        ]),
        'recent_cards': [
            _recent_card('Resumo técnico', 'monitor_heart', 'Sem detalhes disponíveis', [
                {'title': 'Servidor de e-mail', 'meta': email_status['email_host'], 'status': 'Pronto' if email_status['smtp_configured'] else 'Atenção', 'url': ''},
                {'title': 'Porta de envio', 'meta': email_status['email_port'], 'status': 'Configuração SMTP', 'url': ''},
                {
                    'title': 'Arquivos na biblioteca',
                    'meta': f'{media_files} arquivo(s) em {media_folders} pasta(s)',
                    'status': 'Mídia',
                    'url': _admin_url('admin:media_library_mediafile_changelist') if _can(user, 'media_library.view_mediafile') else '',
                },
            ]) if user.is_superuser else None,
        ],
        'empty_message': 'Você ainda não tem permissões para acessar o gerenciamento do sistema.',
    }
    guide['recent_cards'] = _visible(guide['recent_cards'])
    return _guide_response(request, guide)
