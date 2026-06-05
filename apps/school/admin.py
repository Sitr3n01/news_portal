from django.contrib import admin
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin, SuperuserOnlyAdminMixin

from .models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial

VISIBLE_PAGE_SLUGS = ['cursos']
VISIBLE_FEATURE_PLACEMENTS = [
    SchoolFeature.Placement.TRUST,
    SchoolFeature.Placement.LIFE,
]


def _localized_fields(*field_names):
    fields = []
    for field_name in field_names:
        fields.extend([field_name, f'{field_name}_en'])
    return tuple(fields)


@admin.register(Page)
class PageAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'site', 'slug', 'is_published', 'order', 'updated_at']
    list_filter = ['is_published', 'site']
    list_filter_submit = True
    search_fields = ['title', 'slug', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Página Cursos'
    ux_list_description = 'Gerencie a publicação e SEO da página Cursos exibida no front da Komuniki. O conteúdo visual dos cursos é mantido no código atual.'
    ux_list_icon = 'article'
    ux_list_actions = [
        {'label': 'Voltar ao guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Ver cursos', 'icon': 'open_in_new', 'url': '/cursos/', 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Publicadas', 'icon': 'visibility', 'url': '?is_published__exact=1'},
        {'label': 'Não publicadas', 'icon': 'visibility_off', 'url': '?is_published__exact=0'},
    ]
    ux_empty_message = 'Nenhuma página Cursos encontrada. A página deve existir para o link Cursos do front funcionar.'
    ux_form_title = 'Página Cursos'
    ux_form_description = 'Controle publicação e SEO da página Cursos. Campos que não aparecem no front atual ficam visíveis apenas para superusuários.'
    ux_form_icon = 'article'
    ux_form_steps = [
        'Confirme que a página está publicada.',
        'Revise título e descrição SEO usados no navegador e em buscadores.',
        'Use o guia Komuniki para conferir se o link público continua acessível.',
    ]
    ux_after_save_description = 'Depois de salvar, abra a página Cursos e confira a navegação pública.'
    ux_after_save_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Página Cursos', 'icon': 'open_in_new', 'url': '/cursos/'},
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(slug__in=VISIBLE_PAGE_SLUGS)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields.extend(['site', 'slug'])
        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        return [
            ('Página Cursos', {
                'fields': ('site', 'title', 'slug', 'is_published'),
                'classes': ('tab',),
            }),
            ('SEO', {
                'fields': ('meta_title', 'meta_description', 'meta_keywords'),
                'classes': ('tab',),
            }),
        ]


@admin.register(SchoolHomeConfig)
class SchoolHomeConfigAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['site', 'hero_title', 'is_active', 'updated_at']
    list_filter = ['is_active', 'site']
    list_filter_submit = True
    search_fields = [
        'hero_title',
        'hero_title_en',
        'hero_subtitle',
        'hero_subtitle_en',
        'proposal_title',
        'proposal_title_en',
        'life_title',
        'life_title_en',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Home Komuniki'
    ux_list_description = 'A home é o centro da presença da Komuniki: hero, blocos de comunicação, cursos, projetos, depoimentos e contato.'
    ux_list_icon = 'home'
    ux_list_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Nova home', 'icon': 'add_home', 'url': reverse_lazy('admin:school_schoolhomeconfig_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativas', 'icon': 'toggle_on', 'url': '?is_active__exact=1'},
        {'label': 'Inativas', 'icon': 'toggle_off', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhuma home Komuniki configurada. Crie uma configuração ativa antes de divulgar o site.'
    ux_form_title = 'Configuração da Home Komuniki'
    ux_form_description = 'Edite apenas os textos que aparecem na home atual da Komuniki. Campos legados ficam guardados para superusuários.'
    ux_form_icon = 'home'
    ux_form_steps = [
        'Comece pelo hero: selo, título e subtítulo precisam responder quem é a Komuniki.',
        'Depois ajuste composição visual, cursos, projetos e depoimentos com textos objetivos.',
        'Finalize as chamadas de cursos e contato para orientar o próximo passo do visitante.',
    ]
    ux_after_save_description = 'A home depende também dos blocos ativos e depoimentos destacados para ficar completa.'
    ux_after_save_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Blocos da Home', 'icon': 'auto_awesome', 'url': reverse_lazy('admin:school_schoolfeature_changelist')},
        {'label': 'Depoimentos', 'icon': 'format_quote', 'url': reverse_lazy('admin:school_testimonial_changelist')},
    ]
    fieldsets = [
        ('Site', {
            'fields': ('site', 'is_active'),
            'description': 'Cada site deve ter no máximo uma configuração de home escolar.',
            'classes': ('tab',),
        }),
        ('Hero', {
            'fields': _localized_fields('hero_badge', 'hero_title', 'hero_subtitle'),
            'classes': ('tab',),
        }),
        ('Composição visual do hero', {
            'fields': _localized_fields('visual_eyebrow', 'visual_title', 'visual_footer_title', 'visual_footer_text'),
            'classes': ('tab',),
        }),
        ('Seção: proposta pedagógica', {
            'fields': _localized_fields('proposal_eyebrow', 'proposal_title', 'proposal_description'),
            'classes': ('tab',),
        }),
        ('Seção: vida escolar', {
            'fields': _localized_fields('life_eyebrow', 'life_title', 'life_description'),
            'classes': ('tab',),
        }),
        ('Seção: equipe', {
            'fields': _localized_fields('team_eyebrow', 'team_title', 'team_description'),
            'classes': ('tab',),
        }),
        ('Seção: depoimentos', {
            'fields': _localized_fields('testimonials_eyebrow', 'testimonials_title', 'testimonials_description'),
            'classes': ('tab',),
        }),
        ('Chamadas finais', {
            'fields': _localized_fields('hiring_title', 'hiring_description', 'contact_title', 'contact_description'),
            'classes': ('tab',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_title_en', 'meta_description', 'meta_description_en', 'meta_keywords', 'meta_keywords_en'),
            'classes': ('tab',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        return [
            ('Site', {
                'fields': ('site', 'is_active'),
                'description': 'Cada site deve ter no máximo uma configuração ativa de home.',
                'classes': ('tab',),
            }),
            ('Hero', {
                'fields': _localized_fields('hero_badge', 'hero_title', 'hero_subtitle'),
                'classes': ('tab',),
            }),
            ('Composição visual do hero', {
                'fields': _localized_fields('visual_eyebrow', 'visual_title', 'visual_footer_title', 'visual_footer_text'),
                'classes': ('tab',),
            }),
            ('Cursos e projetos', {
                'fields': _localized_fields('proposal_eyebrow', 'proposal_description', 'life_eyebrow', 'life_title', 'life_description'),
                'description': 'O título e os cards de cursos são mantidos no código atual; estes textos são os que aparecem ao redor da grade.',
                'classes': ('tab',),
            }),
            ('Depoimentos', {
                'fields': _localized_fields('testimonials_eyebrow', 'testimonials_title', 'testimonials_description'),
                'classes': ('tab',),
            }),
            ('Chamadas finais', {
                'fields': _localized_fields('hiring_title', 'hiring_description', 'contact_title', 'contact_description'),
                'classes': ('tab',),
            }),
            ('SEO', {
                'fields': ('meta_title', 'meta_title_en', 'meta_description', 'meta_description_en', 'meta_keywords', 'meta_keywords_en'),
                'classes': ('tab',),
            }),
        ]


@admin.register(SchoolFeature)
class SchoolFeatureAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'site', 'placement', 'tone', 'is_active', 'order']
    list_filter = ['site', 'placement', 'tone', 'is_active']
    list_filter_submit = True
    search_fields = ['title', 'title_en', 'description', 'description_en']
    ordering = ['site', 'placement', 'order', 'title']
    readonly_fields = ['created_at', 'updated_at']
    radio_fields = {'placement': admin.HORIZONTAL, 'tone': admin.HORIZONTAL}
    ux_list_title = 'Blocos da Home'
    ux_list_description = 'Cadastre os blocos curtos que aparecem na home atual da Komuniki.'
    ux_list_icon = 'auto_awesome'
    ux_list_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo bloco', 'icon': 'add', 'url': reverse_lazy('admin:school_schoolfeature_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativos', 'icon': 'toggle_on', 'url': '?is_active__exact=1'},
        {'label': 'Inativos', 'icon': 'toggle_off', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhum bloco cadastrado. Adicione blocos para completar a home da Komuniki.'
    ux_form_title = 'Bloco da Home'
    ux_form_description = 'Cada bloco deve ser curto, específico e posicionado apenas em seções que aparecem no front atual.'
    ux_form_icon = 'auto_awesome'
    ux_form_steps = [
        'Escolha onde o bloco aparecerá.',
        'Use título direto e descrição curta.',
        'Defina tom visual e ordem para organizar a leitura.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Todos os blocos', 'icon': 'list', 'url': reverse_lazy('admin:school_schoolfeature_changelist')},
    ]
    fieldsets = [
        ('Conteúdo', {
            'fields': ('site', 'placement', 'title', 'title_en', 'description', 'description_en'),
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(placement__in=VISIBLE_FEATURE_PLACEMENTS)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'placement' and not request.user.is_superuser:
            kwargs['choices'] = [
                choice
                for choice in SchoolFeature.Placement.choices
                if choice[0] in VISIBLE_FEATURE_PLACEMENTS
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(TeamMember)
class TeamMemberAdmin(SuperuserOnlyAdminMixin, AdminUXMixin, ModelAdmin):
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
class TestimonialAdmin(SuperuserOnlyAdminMixin, AdminUXMixin, ModelAdmin):
    list_display = ['name', 'site', 'relationship', 'is_featured', 'created_at']
    list_filter = ['site', 'is_featured']
    list_filter_submit = True
    search_fields = ['name', 'relationship', 'relationship_en', 'quote', 'quote_en']
    readonly_fields = ['created_at', 'updated_at']
    ux_list_title = 'Depoimentos e prova social'
    ux_list_description = 'Use relatos reais para mostrar confiança. A home exibe apenas depoimentos destacados.'
    ux_list_icon = 'format_quote'
    ux_list_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo depoimento', 'icon': 'add_comment', 'url': reverse_lazy('admin:school_testimonial_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Destacados', 'icon': 'stars', 'url': '?is_featured__exact=1'},
        {'label': 'Não destacados', 'icon': 'star_outline', 'url': '?is_featured__exact=0'},
    ]
    ux_empty_message = 'Nenhum depoimento cadastrado. Adicione relatos para fortalecer a apresentação da Komuniki.'
    ux_form_title = 'Depoimento'
    ux_form_description = 'Registre relatos curtos, com identificação clara e destaque apenas os mais fortes para a home.'
    ux_form_icon = 'format_quote'
    ux_form_steps = [
        'Informe nome e relação com a Komuniki.',
        'Mantenha a citação fiel e concisa.',
        'Use destaque quando o depoimento deve aparecer na home.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia Komuniki', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Todos os depoimentos', 'icon': 'format_quote', 'url': reverse_lazy('admin:school_testimonial_changelist')},
    ]
    fieldsets = [
        ('Depoimento', {
            'fields': ('site', 'name', 'relationship', 'relationship_en', 'quote', 'quote_en', 'photo'),
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
