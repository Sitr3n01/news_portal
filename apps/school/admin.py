from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ['title', 'site', 'slug', 'is_published', 'order', 'updated_at']
    list_filter = ['is_published', 'site']
    search_fields = ['title', 'slug', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Conteúdo', {
            'fields': ('site', 'title', 'slug', 'content', 'featured_image'),
        }),
        ('Publicação', {
            'fields': ('is_published', 'order'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(SchoolHomeConfig)
class SchoolHomeConfigAdmin(ModelAdmin):
    list_display = ['site', 'hero_title', 'is_active', 'updated_at']
    list_filter = ['is_active', 'site']
    search_fields = ['hero_title', 'hero_subtitle', 'proposal_title', 'life_title']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Site', {
            'fields': ('site', 'is_active'),
            'description': 'Cada site deve ter no máximo uma configuração de home escolar.',
        }),
        ('Hero', {
            'fields': ('hero_badge', 'hero_title', 'hero_subtitle'),
        }),
        ('Composição visual do hero', {
            'fields': ('visual_eyebrow', 'visual_title', 'visual_footer_title', 'visual_footer_text'),
        }),
        ('Seção: proposta pedagógica', {
            'fields': ('proposal_eyebrow', 'proposal_title', 'proposal_description'),
        }),
        ('Seção: vida escolar', {
            'fields': ('life_eyebrow', 'life_title', 'life_description'),
        }),
        ('Seção: equipe', {
            'fields': ('team_eyebrow', 'team_title', 'team_description'),
        }),
        ('Seção: depoimentos', {
            'fields': ('testimonials_eyebrow', 'testimonials_title', 'testimonials_description'),
        }),
        ('Chamadas finais', {
            'fields': ('hiring_title', 'hiring_description', 'contact_title', 'contact_description'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]


@admin.register(SchoolFeature)
class SchoolFeatureAdmin(ModelAdmin):
    list_display = ['title', 'site', 'placement', 'tone', 'is_active', 'order']
    list_filter = ['site', 'placement', 'tone', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['site', 'placement', 'order', 'title']
    readonly_fields = ['created_at', 'updated_at']
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
class TeamMemberAdmin(ModelAdmin):
    list_display = ['name', 'site', 'title', 'is_active', 'order']
    list_filter = ['site', 'is_active']
    search_fields = ['name', 'title', 'bio', 'email']
    ordering = ['site', 'order', 'name']
    readonly_fields = ['created_at', 'updated_at']
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
class TestimonialAdmin(ModelAdmin):
    list_display = ['name', 'site', 'relationship', 'is_featured', 'created_at']
    list_filter = ['site', 'is_featured']
    search_fields = ['name', 'relationship', 'quote']
    readonly_fields = ['created_at', 'updated_at']
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
