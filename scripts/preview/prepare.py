"""Create independent local datasets, without replacing an existing preview."""
import os
import shutil
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'news_portal'
PREVIEW = ROOT / '.preview'
sys.path.insert(0, str(ROOT))


def prepare_copies():
    if ROOT.resolve() == SOURCE.resolve():
        raise RuntimeError('Preview and source must be different directories.')
    PREVIEW.mkdir(exist_ok=True)
    source_db = SOURCE / 'db.sqlite3'
    if not source_db.is_file():
        raise FileNotFoundError(source_db)
    for scenario in ('current', 'demo'):
        destination = PREVIEW / f'{scenario}.sqlite3'
        if not destination.exists():
            with sqlite3.connect(source_db.as_uri() + '?mode=ro', uri=True) as original:
                with sqlite3.connect(destination) as copy:
                    original.backup(copy)
            print(f'Created independent database: {destination}')
        media = PREVIEW / f'{scenario}-media'
        if not media.exists():
            shutil.copytree(SOURCE / 'media', media)


def prepare_demo():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.design_preview'
    os.environ['KOMUNIKI_PREVIEW_SCENARIO'] = 'demo'
    import django
    django.setup()

    from django.conf import settings
    from django.contrib.sites.models import Site
    from django.db import transaction

    from apps.school.models import Page, SchoolHomeConfig
    from apps.school.models import Testimonial as SchoolTestimonial
    from apps.social.models import MediaType, Platform, SocialAccount, SocialPost

    expected = PREVIEW / 'demo.sqlite3'
    if Path(settings.DATABASES['default']['NAME']).resolve() != expected.resolve():
        raise RuntimeError('Demo preparation must only target .preview/demo.sqlite3.')
    marker = PREVIEW / 'demo-prepared.txt'
    if marker.exists():
        print('Demo already prepared; existing data retained.')
        return

    # The illustrative asset is used as sample media, never as a person's photo.
    demo_media = Path(settings.MEDIA_ROOT) / 'demo'
    demo_media.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'static/images/komuniki-editorial-hero.png', demo_media / 'sculpture.png')
    with transaction.atomic():
        site = Site.objects.get(pk=settings.SITE_ID)
        config = SchoolHomeConfig.objects.get(site=site)
        config.testimonials_title = 'Espaço para novas histórias'
        config.testimonials_title_en = 'Room for new stories'
        config.testimonials_description = 'Demonstração visual: os relatos abaixo são fictícios e não representam alunos ou experiências reais.'
        config.testimonials_description_en = 'Visual demonstration: the stories below are fictional and do not represent real students or experiences.'
        config.save(update_fields=['testimonials_title', 'testimonials_title_en', 'testimonials_description', 'testimonials_description_en'])
        for number in range(1, 4):
            SchoolTestimonial.objects.create(
                site=site, name=f'Participante de teste {number}',
                relationship='DEMONSTRAÇÃO · conteúdo fictício',
                relationship_en='DEMONSTRATION · fictional content',
                quote='Este é um texto de demonstração para conferir a leitura de um depoimento, seu espaçamento e a identificação de quem participa.',
                quote_en='This is demonstration text to review the readability of a testimonial, its spacing and the participant identification.',
                is_featured=True,
                # A clearly labelled abstract illustration exercises the image branch.
                photo='demo/sculpture.png' if number == 1 else '',
            )
        extension = site.extension
        extension.social_section_enabled = True
        extension.social_show_instagram = True
        extension.social_show_tiktok = True
        extension.social_section_title = 'Comunicação em movimento'
        extension.social_section_title_en = 'Communication in motion'
        extension.social_section_subtitle = 'DEMONSTRAÇÃO — publicações fictícias para testar cartões com imagem, sem imagem e com indicação de vídeo.'
        extension.social_section_subtitle_en = 'DEMONSTRATION — fictional posts to test cards with images, without images and with video indicators.'
        extension.instagram_url = 'https://www.instagram.com/komunikiescola/'
        extension.save()
        sample_page = Page.objects.create(
            site=site, slug='demonstracao-editorial',
            title='Demonstração: comunicação, artes e liderança para transformar ideias em projetos e possibilidades profissionais',
            is_published=True, featured_image='demo/sculpture.png',
            content=(
                '<h2>Conteúdo fictício para revisão</h2>'
                '<p>Esta página local demonstra o template de conteúdo do CMS. Nenhuma publicação social real é representada aqui.</p>'
                '<ul><li>Imagem ilustrativa</li><li>Texto e links preservados pelo CMS</li></ul>'
                '<p><a href="/">Voltar ao início</a></p>'
            ),
        )
        for number in range(1, 7):
            platform = Platform.INSTAGRAM if number % 2 else Platform.TIKTOK
            account, _ = SocialAccount.objects.get_or_create(
                site=site, platform=platform, username='editorial_demo',
                defaults={'display_name': f'DEMONSTRAÇÃO {platform}', 'is_active': True},
            )
            SocialPost.objects.create(
                account=account,
                external_id=f'komuniki-editorial-demo-{number}',
                permalink=f'http://127.0.0.1:8012/{sample_page.slug}/',
                caption=f'DEMONSTRAÇÃO {number:02d} — Conteúdo fictício para explorar comunicação, artes e presença. Este cartão serve apenas à avaliação visual.',
                media_type=MediaType.VIDEO if number % 3 == 0 else MediaType.IMAGE,
                thumbnail_image='demo/sculpture.png' if number % 2 else '',
                published_at=datetime(2026, 9, 8, 12, tzinfo=UTC) - timedelta(days=number),
            )
    marker.write_text('Local synthetic content created. Do not publish these databases.\n', encoding='utf-8')
    print('Created 3 fictional testimonials, 6 fictional posts and one demo CMS page.')


if __name__ == '__main__':
    prepare_copies()
    prepare_demo()
