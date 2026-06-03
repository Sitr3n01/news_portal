from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.shortcuts import render

from apps.common.admin_nav import (
    MANAGEMENT_PERMISSIONS,
    NEWS_PERMISSIONS,
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
    from apps.hiring.models import Application, JobPosting
    from apps.school.models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial

    user = request.user
    has_access = _can_any(user, SCHOOL_PERMISSIONS)
    home_configs = SchoolHomeConfig.objects.filter(is_active=True).count()
    published_pages = Page.objects.filter(is_published=True).count()
    active_features = SchoolFeature.objects.filter(is_active=True).count()
    active_team = TeamMember.objects.filter(is_active=True).count()
    featured_testimonials = Testimonial.objects.filter(is_featured=True).count()
    open_jobs = JobPosting.objects.filter(status=JobPosting.Status.OPEN).count()
    received_applications = Application.objects.filter(status=Application.Status.RECEIVED).count()
    unread_messages = ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW).count()

    recent_applications = [
        {
            'title': f'{application.first_name} {application.last_name}',
            'meta': f'Candidatura para {application.job.title}',
            'url': _admin_url('admin:hiring_application_change', args=[application.pk]),
            'status': application.get_status_display(),
        }
        for application in Application.objects.select_related('job').order_by('-created_at')[:5]
    ] if _can(user, 'hiring.view_application') else []

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
        'eyebrow': 'Portal Escolar',
        'title': 'Operação do Portal Escolar',
        'subtitle': 'Gerencie conteúdo institucional, equipe, prova social, contatos e contratação em uma sequência clara.',
        'icon': 'school',
        'primary_actions': _visible([
            _action(user, 'Editar home escolar', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig', kind='primary'),
            _public_action('Ver portal escolar', 'open_in_new', '/'),
            _action(user, 'Mensagens novas', 'mail', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry', query={'status__exact': ContactInquiry.Status.NEW}),
        ]),
        'metrics': [
            _metric('Home ativa', home_configs, 'home', 'success' if home_configs else 'warning', 'Configuração principal'),
            _metric('Páginas publicadas', published_pages, 'article', 'primary' if published_pages else 'neutral', 'Conteúdo institucional'),
            _metric('Vagas abertas', open_jobs, 'work', 'primary' if open_jobs else 'neutral', 'Oportunidades visíveis'),
            _metric('Pendências humanas', received_applications + unread_messages, 'priority_high', 'warning' if received_applications or unread_messages else 'neutral', 'Candidaturas e mensagens'),
        ],
        'workflows': [
            _workflow(
                'Configurar presença institucional',
                'home',
                'Comece pela home, depois publique páginas e diferenciais para apresentar a escola com clareza.',
                'Pronto' if home_configs and published_pages and active_features else 'Atenção',
                'success' if home_configs and published_pages and active_features else 'warning',
                [
                    _action(user, 'Home escolar', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig', kind='primary'),
                    _action(user, 'Páginas', 'article', 'admin:school_page_changelist', 'school.view_page'),
                    _action(user, 'Diferenciais', 'auto_awesome', 'admin:school_schoolfeature_changelist', 'school.view_schoolfeature'),
                ],
            ),
            _workflow(
                'Manter equipe e prova social',
                'groups',
                'Atualize educadores e depoimentos para manter confiança e contexto para famílias.',
                'Completo' if active_team and featured_testimonials else 'Completar',
                'success' if active_team and featured_testimonials else 'warning',
                [
                    _action(user, 'Equipe', 'group', 'admin:school_teammember_changelist', 'school.view_teammember', kind='primary'),
                    _action(user, 'Depoimentos', 'format_quote', 'admin:school_testimonial_changelist', 'school.view_testimonial'),
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
            _workflow(
                'Gerenciar contratações',
                'work',
                'Abra vagas quando houver oportunidades e revise candidaturas recebidas sem perder histórico.',
                'Aguardando análise' if received_applications else 'Sem novas candidaturas',
                'warning' if received_applications else 'neutral',
                [
                    _action(user, 'Abrir vaga', 'add_business', 'admin:hiring_jobposting_add', 'hiring.add_jobposting', kind='primary'),
                    _action(user, 'Candidaturas recebidas', 'description', 'admin:hiring_application_changelist', 'hiring.view_application', query={'status__exact': Application.Status.RECEIVED}),
                    _action(user, 'Departamentos', 'business', 'admin:hiring_department_changelist', 'hiring.view_department'),
                ],
            ),
        ],
        'readiness': [
            _check(
                'Home escolar ativa',
                bool(home_configs),
                'Configure a página inicial antes de divulgar o portal.',
                _admin_url('admin:school_schoolhomeconfig_changelist') if _can(user, 'school.view_schoolhomeconfig') else '',
            ),
            _check(
                'Páginas institucionais publicadas',
                published_pages > 0,
                'Publique páginas essenciais como sobre, proposta e privacidade.',
                _admin_url('admin:school_page_changelist') if _can(user, 'school.view_page') else '',
            ),
            _check(
                'Diferenciais ativos',
                active_features > 0,
                'Cadastre benefícios e pontos fortes exibidos na home.',
                _admin_url('admin:school_schoolfeature_changelist') if _can(user, 'school.view_schoolfeature') else '',
            ),
            _check(
                'Equipe visível',
                active_team > 0,
                'Mostre pessoas responsáveis pela experiência escolar.',
                _admin_url('admin:school_teammember_changelist') if _can(user, 'school.view_teammember') else '',
            ),
            _check(
                'Depoimentos destacados',
                featured_testimonials > 0,
                'Use relatos para reforçar confiança.',
                _admin_url('admin:school_testimonial_changelist') if _can(user, 'school.view_testimonial') else '',
            ),
        ],
        'resources': _visible([
            _resource_group('Conteúdo institucional', 'Textos e blocos que explicam a escola para famílias e comunidade.', [
                _action(user, 'Home escolar', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig'),
                _action(user, 'Páginas', 'article', 'admin:school_page_changelist', 'school.view_page'),
                _action(user, 'Diferenciais', 'auto_awesome', 'admin:school_schoolfeature_changelist', 'school.view_schoolfeature'),
            ]),
            _resource_group('Relacionamento', 'Pessoas, relatos e mensagens recebidas pelo site.', [
                _action(user, 'Equipe', 'group', 'admin:school_teammember_changelist', 'school.view_teammember'),
                _action(user, 'Depoimentos', 'format_quote', 'admin:school_testimonial_changelist', 'school.view_testimonial'),
                _action(user, 'Mensagens', 'contact_mail', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry'),
            ]),
            _resource_group('Contratações', 'Vagas abertas e acompanhamento de candidatos.', [
                _action(user, 'Vagas', 'work', 'admin:hiring_jobposting_changelist', 'hiring.view_jobposting'),
                _action(user, 'Candidaturas', 'description', 'admin:hiring_application_changelist', 'hiring.view_application'),
                _action(user, 'Departamentos', 'business', 'admin:hiring_department_changelist', 'hiring.view_department'),
            ]),
        ]),
        'recent_cards': _visible([
            _recent_card('Candidaturas recentes', 'description', 'Nenhuma candidatura recente', recent_applications) if _can(user, 'hiring.view_application') else None,
            _recent_card('Mensagens recentes', 'mail', 'Nenhuma mensagem recente', recent_messages) if _can(user, 'contact.view_contactinquiry') else None,
        ]),
        'empty_message': 'Você ainda não tem permissões para operar o Portal Escolar.',
    }
    return _guide_response(request, guide)


def news_guide(request):
    from apps.news.models import Article, Category, Comment, NewsletterDelivery, NewsletterSubscription, Tag

    user = request.user
    has_access = _can_any(user, NEWS_PERMISSIONS)
    published_articles = Article.objects.filter(status=Article.Status.PUBLISHED).count()
    draft_articles = Article.objects.filter(status=Article.Status.DRAFT).count()
    pending_newsletter_articles = Article.objects.filter(status=Article.Status.PUBLISHED, newsletter_sent_at__isnull=True).count()
    categories = Category.objects.count()
    tags = Tag.objects.count()
    pending_comments = Comment.objects.filter(is_active=False).count()
    active_subscribers = NewsletterSubscription.objects.filter(is_active=True).count()
    failed_deliveries = NewsletterDelivery.objects.filter(status=NewsletterDelivery.Status.FAILED).count()
    pending_deliveries = NewsletterDelivery.objects.filter(status=NewsletterDelivery.Status.PENDING).count()

    recent_articles = [
        {
            'title': article.title,
            'meta': article.get_status_display(),
            'url': _admin_url('admin:news_article_change', args=[article.pk]),
            'status': article.updated_at,
        }
        for article in Article.objects.select_related('category').order_by('-updated_at')[:5]
    ] if _can(user, 'news.view_article') else []

    guide = {
        'area': 'news',
        'has_access': has_access,
        'eyebrow': 'Portal de Notícias',
        'title': 'Operação Editorial',
        'subtitle': 'Conduza o ciclo editorial completo: criar, organizar, publicar, enviar newsletter e moderar a comunidade.',
        'icon': 'newspaper',
        'primary_actions': _visible([
            _action(user, 'Novo artigo', 'edit_square', 'admin:news_article_add', 'news.add_article', kind='primary'),
            _public_action('Ver portal de notícias', 'open_in_new', '/news/'),
            _action(user, 'Comentários pendentes', 'rate_review', 'admin:news_comment_changelist', 'news.view_comment', query={'is_active__exact': '0'}),
        ]),
        'metrics': [
            _metric('Publicados', published_articles, 'check_circle', 'primary', 'Artigos visíveis'),
            _metric('Rascunhos', draft_articles, 'edit_note', 'warning' if draft_articles else 'neutral', 'Conteúdo em preparo'),
            _metric('Assinantes ativos', active_subscribers, 'group', 'primary', 'Newsletter'),
            _metric(
                'Pendências',
                pending_comments + failed_deliveries + pending_deliveries + pending_newsletter_articles,
                'priority_high',
                'warning' if pending_comments or failed_deliveries or pending_deliveries or pending_newsletter_articles else 'neutral',
                'Moderação e newsletter',
            ),
        ],
        'workflows': [
            _workflow(
                'Criar rascunho',
                'edit_square',
                'Escreva o artigo, adicione resumo e mantenha como rascunho até estar pronto.',
                'Rascunhos ativos' if draft_articles else 'Sem rascunhos',
                'warning' if draft_articles else 'neutral',
                [
                    _action(user, 'Novo artigo', 'edit_square', 'admin:news_article_add', 'news.add_article', kind='primary'),
                    _action(user, 'Ver rascunhos', 'edit_note', 'admin:news_article_changelist', 'news.view_article', query={'status__exact': Article.Status.DRAFT}),
                ],
            ),
            _workflow(
                'Organizar editoria',
                'category',
                'Categorias e tags ajudam leitores a navegar e melhoram a busca interna.',
                'Organizado' if categories and tags else 'Completar taxonomia',
                'success' if categories and tags else 'warning',
                [
                    _action(user, 'Categorias', 'category', 'admin:news_category_changelist', 'news.view_category', kind='primary'),
                    _action(user, 'Tags', 'label', 'admin:news_tag_changelist', 'news.view_tag'),
                ],
            ),
            _workflow(
                'Publicar e distribuir',
                'mark_email_read',
                'Depois de publicar, acompanhe artigos aguardando newsletter e entregas com falha.',
                'Revisar envio' if failed_deliveries or pending_newsletter_articles else 'Tudo enviado',
                'danger' if failed_deliveries else ('warning' if pending_newsletter_articles else 'success'),
                [
                    _action(user, 'Aguardando newsletter', 'outbox', 'admin:news_article_changelist', 'news.view_article', query={'newsletter': 'pending'}, kind='primary'),
                    _action(user, 'Entregas com falha', 'error', 'admin:news_newsletterdelivery_changelist', 'news.view_newsletterdelivery', query={'status__exact': NewsletterDelivery.Status.FAILED}),
                    _action(user, 'Assinantes', 'mail', 'admin:news_newslettersubscription_changelist', 'news.view_newslettersubscription'),
                ],
            ),
            _workflow(
                'Moderar comunidade',
                'forum',
                'Revise comentários ocultos ou pendentes para manter a conversa saudável.',
                'Requer moderação' if pending_comments else 'Tudo em dia',
                'warning' if pending_comments else 'success',
                [
                    _action(user, 'Comentários pendentes', 'rate_review', 'admin:news_comment_changelist', 'news.view_comment', query={'is_active__exact': '0'}, kind='primary'),
                    _action(user, 'Todos os comentários', 'chat', 'admin:news_comment_changelist', 'news.view_comment'),
                ],
            ),
        ],
        'readiness': [
            _check(
                'Ao menos uma categoria',
                categories > 0,
                'Categorias estruturam o portal.',
                _admin_url('admin:news_category_changelist') if _can(user, 'news.view_category') else '',
            ),
            _check(
                'Artigos publicados',
                published_articles > 0,
                'Publique conteúdo para alimentar a home de notícias.',
                _admin_url('admin:news_article_changelist', {'status__exact': Article.Status.PUBLISHED}) if _can(user, 'news.view_article') else '',
            ),
            _check(
                'Sem comentários pendentes',
                pending_comments == 0,
                'Comentários pendentes precisam de revisão.',
                _admin_url('admin:news_comment_changelist', {'is_active__exact': '0'}) if _can(user, 'news.view_comment') else '',
            ),
            _check(
                'Newsletter sem falhas',
                failed_deliveries == 0,
                'Falhas indicam problema de envio ou destinatário.',
                _admin_url('admin:news_newsletterdelivery_changelist', {'status__exact': NewsletterDelivery.Status.FAILED}) if _can(user, 'news.view_newsletterdelivery') else '',
            ),
        ],
        'resources': _visible([
            _resource_group('Produção editorial', 'Criação, organização e publicação de conteúdo.', [
                _action(user, 'Artigos', 'newspaper', 'admin:news_article_changelist', 'news.view_article'),
                _action(user, 'Categorias', 'category', 'admin:news_category_changelist', 'news.view_category'),
                _action(user, 'Tags', 'label', 'admin:news_tag_changelist', 'news.view_tag'),
            ]),
            _resource_group('Comunidade e newsletter', 'Relacionamento com leitores, comentários e entregas.', [
                _action(user, 'Comentários', 'chat', 'admin:news_comment_changelist', 'news.view_comment'),
                _action(user, 'Assinantes', 'mail', 'admin:news_newslettersubscription_changelist', 'news.view_newslettersubscription'),
                _action(user, 'Entregas', 'mark_email_read', 'admin:news_newsletterdelivery_changelist', 'news.view_newsletterdelivery'),
            ]),
        ]),
        'recent_cards': _visible([
            _recent_card('Artigos recentes', 'newspaper', 'Nenhum artigo recente', recent_articles) if _can(user, 'news.view_article') else None,
        ]),
        'empty_message': 'Você ainda não tem permissões para operar o Portal de Notícias.',
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
            _action(user, 'Configurações dos sites', 'settings', 'admin:common_siteextension_changelist', 'common.view_siteextension'),
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
                    _action(user, 'Configurações dos sites', 'settings', 'admin:common_siteextension_changelist', 'common.view_siteextension', kind='primary'),
                    _action(user, 'Domínios e sites', 'language', 'admin:sites_site_changelist', 'sites.view_site'),
                ],
            ),
            _workflow(
                'Envio de e-mails',
                'outgoing_mail',
                'Acompanhe SMTP, remetentes por site e falhas de newsletter sem expor detalhes técnicos para toda equipe.',
                'Atenção' if not email_ready or failed_deliveries else 'Tudo saudável',
                'danger' if failed_deliveries else ('warning' if not email_ready else 'success'),
                [
                    _action(user, 'Configurar remetentes', 'settings_account_box', 'admin:common_siteextension_changelist', 'common.view_siteextension', kind='primary'),
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
            _check('Sites cadastrados', sites > 0, 'O Sites Framework define contexto dos portais.', _admin_url('admin:sites_site_changelist') if _can(user, 'sites.view_site') else ''),
            _check(
                'Contatos dos sites configurados',
                configured_sites >= sites and sites > 0,
                'Preencha e-mail, telefone e identidade pública.',
                _admin_url('admin:common_siteextension_changelist') if _can(user, 'common.view_siteextension') else '',
            ),
            _check(
                'Remetente da newsletter configurado',
                sender_sites > 0,
                'Cada site precisa de remetente amigável para envios.',
                _admin_url('admin:common_siteextension_changelist') if _can(user, 'common.view_siteextension') else '',
            ),
            _check('Servidor de e-mail pronto', email_status['smtp_configured'], 'Configuração SMTP completa libera envios reais.', ''),
        ],
        'resources': _visible([
            _resource_group('Acessos', 'Usuários e perfis administrativos.', [
                _action(user, 'Usuários', 'manage_accounts', 'admin:accounts_customuser_changelist', 'accounts.view_customuser'),
                _action(user, 'Grupos de permissões', 'badge', 'admin:auth_group_changelist', 'auth.view_group'),
            ]),
            _resource_group('Sites e configuração', 'Identidade, domínios e remetentes.', [
                _action(user, 'Configurações dos sites', 'settings', 'admin:common_siteextension_changelist', 'common.view_siteextension'),
                _action(user, 'Sites', 'language', 'admin:sites_site_changelist', 'sites.view_site'),
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
