def get_social_section_posts(site):
    """Resolve até 6 SocialPost respeitando os toggles de SiteExtension.

    Retorna lista vazia se não houver SiteExtension, se a seção estiver
    desligada, ou se nenhuma rede estiver habilitada.
    """
    from apps.social.models import Platform, SocialPost

    site_ext = getattr(site, 'extension', None)
    if not site_ext or not site_ext.social_section_enabled:
        return []

    allowed_platforms = []
    if site_ext.social_show_instagram:
        allowed_platforms.append(Platform.INSTAGRAM)
    if site_ext.social_show_tiktok:
        allowed_platforms.append(Platform.TIKTOK)

    if not allowed_platforms:
        return []

    return list(
        SocialPost.objects
        .select_related('account')
        .filter(
            account__site=site, account__is_active=True, is_visible=True,
            platform__in=allowed_platforms,
        )
        .order_by('-published_at')[:6]
    )
