from django.contrib import admin
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial


@admin.register(Page)
class PageAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'site', 'slug', 'is_published', 'order', 'updated_at']
    list_filter = ['is_published', 'site']
    list_filter_submit = True
    search_fields = ['title', 'slug', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Páginas institucionais'
    ux_list_description = 'Use esta tela para manter páginas permanentes da escola, como sobre, proposta, privacidade e conteúdos de apoio.'
    ux_list_icon = 'article'
    ux_list_actions = [
        {'label': 'Voltar ao guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Nova página', 'icon': 'add', 'url': reverse_lazy('admin:school_page_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Publicadas', 'icon': 'visibility', 'url': '?is_published__exact=1'},
        {'label': 'Não publicadas', 'icon': 'visibility_off', 'url': '?is_published__exact=0'},
    ]
    ux_empty_message = 'Nenhuma página encontrada. Crie primeiro as páginas essenciais para apresentar a escola.'
    ux_form_title = 'Página institucional'
    ux_form_description = 'Escreva uma página clara, vinculada ao site correto, e publique apenas quando o conteúdo estiver revisado.'
    ux_form_icon = 'article'
    ux_form_steps = [
        'Escolha o site e confirme o título público.',
        'Revise o conteúdo principal e a imagem destacada.',
        'Publique somente quando a página estiver pronta para visitantes.',
    ]
    ux_after_save_description = 'Depois de salvar, confira a lista de páginas e retorne ao guia para completar o restante do portal escolar.'
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Todas as páginas', 'icon': 'list', 'url': reverse_lazy('admin:school_page_changelist')},
    ]
    fieldsets = [
        ('Conteúdo', {
            'fields': ('site', 'title', 'slug', 'content', 'featured_image'),
            'classes': ('tab',),
        }),
        ('Publicação', {
            'fields': ('is_published', 'order'),
            'classes': ('tab',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('tab',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(SchoolHomeConfig)
class SchoolHomeConfigAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['site', 'hero_title', 'is_active', 'updated_at']
    list_filter = ['is_active', 'site']
    list_filter_submit = True
    search_fields = ['hero_title', 'hero_subtitle', 'proposal_title', 'life_title']
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Home do Portal Escolar'
    ux_list_description = 'A home é o centro da presença institucional: hero, proposta, vida escolar, equipe, depoimentos, vagas e contato.'
    ux_list_icon = 'home'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Nova home', 'icon': 'add_home', 'url': reverse_lazy('admin:school_schoolhomeconfig_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativas', 'icon': 'toggle_on', 'url': '?is_active__exact=1'},
        {'label': 'Inativas', 'icon': 'toggle_off', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhuma home escolar configurada. Crie uma configuração ativa antes de divulgar o portal.'
    ux_form_title = 'Configuração da home escolar'
    ux_form_description = 'Edite a narrativa principal da escola em blocos curtos para manter a página inicial clara e confiável.'
    ux_form_icon = 'home'
    ux_form_steps = [
        'Comece pelo hero: selo, título e subtítulo precisam responder quem é a escola.',
        'Depois ajuste proposta, vida escolar, equipe e depoimentos com textos objetivos.',
        'Finalize chamadas de vagas e contato para orientar o próximo passo do visitante.',
    ]
    ux_after_save_description = 'A home depende também de diferenciais, equipe e depoimentos ativos para ficar completa.'
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Diferenciais', 'icon': 'auto_awesome', 'url': reverse_lazy('admin:school_schoolfeature_changelist')},
        {'label': 'Equipe', 'icon': 'group', 'url': reverse_lazy('admin:school_teammember_changelist')},
        {'label': 'Depoimentos', 'icon': 'format_quote', 'url': reverse_lazy('admin:school_testimonial_changelist')},
    ]
    fieldsets = [
        ('Site', {
            'fields': ('site', 'is_active'),
            'description': 'Cada site deve ter no máximo uma configuração de home escolar.',
            'classes': ('tab',),
        }),
        ('Hero', {
            'fields': ('hero_badge', 'hero_title', 'hero_subtitle'),
            'classes': ('tab',),
        }),
        ('Composição visual do hero', {
            'fields': ('visual_eyebrow', 'visual_title', 'visual_footer_title', 'visual_footer_text'),
            'classes': ('tab',),
        }),
        ('Seção: proposta pedagógica', {
            'fields': ('proposal_eyebrow', 'proposal_title', 'proposal_description'),
            'classes': ('tab',),
        }),
        ('Seção: vida escolar', {
            'fields': ('life_eyebrow', 'life_title', 'life_description'),
            'classes': ('tab',),
        }),
        ('Seção: equipe', {
            'fields': ('team_eyebrow', 'team_title', 'team_description'),
            'classes': ('tab',),
        }),
        ('Seção: depoimentos', {
            'fields': ('testimonials_eyebrow', 'testimonials_title', 'testimonials_description'),
            'classes': ('tab',),
        }),
        ('Chamadas finais', {
            'fields': ('hiring_title', 'hiring_description', 'contact_title', 'contact_description'),
            'classes': ('tab',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('tab',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(SchoolFeature)
class SchoolFeatureAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'site', 'placement', 'tone', 'is_active', 'order']
    list_filter = ['site', 'placement', 'tone', 'is_active']
    list_filter_submit = True
    search_fields = ['title', 'description']
    ordering = ['site', 'placement', 'order', 'title']
    readonly_fields = ['created_at', 'updated_at']
    radio_fields = {'placement': admin.HORIZONTAL, 'tone': admin.HORIZONTAL}
    ux_list_title = 'Diferenciais da escola'
    ux_list_description = 'Cadastre pontos fortes em seções específicas da home para mostrar valor institucional sem textos longos.'
    ux_list_icon = 'auto_awesome'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo diferencial', 'icon': 'add', 'url': reverse_lazy('admin:school_schoolfeature_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativos', 'icon': 'toggle_on', 'url': '?is_active__exact=1'},
        {'label': 'Inativos', 'icon': 'toggle_off', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhum diferencial cadastrado. Adicione benefícios para completar a home escolar.'
    ux_form_title = 'Diferencial da escola'
    ux_form_description = 'Cada diferencial deve ser curto, específico e posicionado na seção onde ajuda mais o visitante.'
    ux_form_icon = 'auto_awesome'
    ux_form_steps = [
        'Escolha onde o diferencial aparecerá.',
        'Use título direto e descrição curta.',
        'Defina tom visual e ordem para organizar a leitura.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Todos os diferenciais', 'icon': 'list', 'url': reverse_lazy('admin:school_schoolfeature_changelist')},
    ]
    fieldsets = [
        ('Conteúdo', {
            'fields': ('site', 'placement', 'title', 'description'),
        }),
        ('Exibição', {
            'fields': ('tone', 'is_active', 'order'),
            'description': 'Use a ordem para controlar a posição dentro da seção escolhida.',
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(TeamMember)
class TeamMemberAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'site', 'title', 'is_active', 'order']
    list_filter = ['site', 'is_active']
    list_filter_submit = True
    search_fields = ['name', 'title', 'bio', 'email']
    ordering = ['site', 'order', 'name']
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Equipe escolar'
    ux_list_description = 'Mantenha pessoas visíveis e bem identificadas para reforçar confiança de famílias e candidatos.'
    ux_list_icon = 'group'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo membro', 'icon': 'person_add', 'url': reverse_lazy('admin:school_teammember_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativos', 'icon': 'visibility', 'url': '?is_active__exact=1'},
        {'label': 'Ocultos', 'icon': 'visibility_off', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhum membro de equipe cadastrado. Adicione pelo menos as lideranças ou responsáveis principais.'
    ux_form_title = 'Perfil de equipe'
    ux_form_description = 'Crie perfis humanos, objetivos e com foto quando possível; isso reduz dúvidas de famílias e visitantes.'
    ux_form_icon = 'badge'
    ux_form_steps = [
        'Inclua nome, função e foto atualizada.',
        'Use uma bio curta, com foco em atuação e vínculo com a escola.',
        'Marque como ativo para aparecer no portal.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Equipe completa', 'icon': 'group', 'url': reverse_lazy('admin:school_teammember_changelist')},
    ]
    fieldsets = [
        ('Identificação', {
            'fields': ('site', 'name', 'title', 'photo'),
        }),
        ('Perfil', {
            'fields': ('bio', 'email'),
            'description': 'O e-mail aparece apenas na página completa de equipe, não na home.',
        }),
        ('Exibição', {
            'fields': ('is_active', 'order'),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(Testimonial)
class TestimonialAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'site', 'relationship', 'is_featured', 'created_at']
    list_filter = ['site', 'is_featured']
    list_filter_submit = True
    search_fields = ['name', 'relationship', 'quote']
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Depoimentos e prova social'
    ux_list_description = 'Use relatos reais para mostrar confiança. A home exibe apenas depoimentos destacados.'
    ux_list_icon = 'format_quote'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo depoimento', 'icon': 'add_comment', 'url': reverse_lazy('admin:school_testimonial_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Destacados', 'icon': 'stars', 'url': '?is_featured__exact=1'},
        {'label': 'Não destacados', 'icon': 'star_outline', 'url': '?is_featured__exact=0'},
    ]
    ux_empty_message = 'Nenhum depoimento cadastrado. Adicione relatos para fortalecer a apresentação da escola.'
    ux_form_title = 'Depoimento'
    ux_form_description = 'Registre relatos curtos, com identificação clara e destaque apenas os mais fortes para a home.'
    ux_form_icon = 'format_quote'
    ux_form_steps = [
        'Informe nome e relação com a escola.',
        'Mantenha a citação fiel e concisa.',
        'Use destaque quando o depoimento deve aparecer na home.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Todos os depoimentos', 'icon': 'format_quote', 'url': reverse_lazy('admin:school_testimonial_changelist')},
    ]
    fieldsets = [
        ('Depoimento', {
            'fields': ('site', 'name', 'relationship', 'quote', 'photo'),
        }),
        ('Exibição', {
            'fields': ('is_featured',),
            'description': 'A home exibe apenas depoimentos destacados do site atual.',
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]
    actions = ['feature_selected', 'unfeature_selected']

    @admin.action(description='Destacar depoimentos selecionados')
    def feature_selected(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} depoimento(s) destacado(s).')

    @admin.action(description='Remover destaque dos depoimentos')
    def unfeature_selected(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} destaque removido de depoimento(s).')
