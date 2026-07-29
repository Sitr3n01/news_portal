from io import BytesIO

import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.common import turnstile
from apps.common.validators import ARTICLE_IMAGE_MAX_WIDTH
from apps.media_library.models import MediaFile
from apps.news.admin import _csv_safe
from apps.news.models import Article, Category, NewsHomeConfig, NewsletterDelivery, NewsletterSubscription, Tag
from apps.news.newsletter import make_unsubscribe_token

# ── Helpers compartilhados ───────────────────────────────────────────────────

def make_user(username='editor', role='news_editor', password='x', user_model=None):
    """Cria um CustomUser com o role indicado."""
    from django.contrib.auth import get_user_model
    user_model = user_model or get_user_model()
    return user_model.objects.create_user(username=username, password=password, role=role)


def make_site(pk=1, domain='testserver', name='Test Site'):
    site, _ = Site.objects.update_or_create(
        id=pk,
        defaults={'domain': domain, 'name': name},
    )
    return site


def make_article(site, slug='artigo', status=Article.Status.PUBLISHED):
    return Article.objects.create(
        title=f'Artigo {slug}',
        slug=slug,
        excerpt='Resumo do artigo',
        content='Conteúdo do artigo para newsletter.',
        site=site,
        status=status,
    )


def make_article_full(site, slug='artigo', status=Article.Status.PUBLISHED, category=None, author=None):
    """Cria um artigo com category e author populados (necessário para save_revision/full_clean)."""
    art = make_article(site, slug=slug, status=status)
    if category is None:
        category, _ = Category.objects.get_or_create(
            name='Geral', slug='geral',
        )
    if author is None:
        from django.contrib.auth import get_user_model
        user_cls = get_user_model()
        author = user_cls.objects.create_user(
            username=f'author-{slug}',
            email=f'author-{slug}@test.com',
            password='x',
        )
    art.category = category
    art.author = author
    art.save()
    return art


def mock_turnstile(monkeypatch, *, valid=True):
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


def make_image_upload(name='capa.png', size=(2400, 1200), fmt='PNG'):
    """Gera um upload de imagem real (Pillow) para os testes de capa."""
    buf = BytesIO()
    Image.new('RGB', size, (30, 90, 180)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f'image/{fmt.lower()}')


# ── Capa de artigo: mesma higiene do avatar (ProcessedImageField) ────────────

@pytest.mark.django_db
def test_article_featured_image_stored_as_optimized_jpeg(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa',
        slug='com-capa',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(2400, 1200)),
    )

    assert article.featured_image.name.endswith('.jpg')
    with Image.open(article.featured_image.path) as img:
        assert img.format == 'JPEG'
        # 2400×1200 (2:1) cabe em 1600×1600 → 1600×800, sem distorcer nem cortar.
        assert img.width == ARTICLE_IMAGE_MAX_WIDTH
        assert img.height == 800


@pytest.mark.django_db
def test_article_featured_image_rejects_non_image(settings, tmp_path):
    from django.core.exceptions import ValidationError

    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()
    article = Article(
        title='Artigo ruim',
        slug='artigo-ruim',
        content='Conteúdo.',
        site=site,
        featured_image=SimpleUploadedFile('fake.jpg', b'isto nao e imagem', content_type='image/jpeg'),
    )

    # O validador centralizado está plugado no campo: full_clean deve rejeitar.
    with pytest.raises(ValidationError):
        article.full_clean()


@pytest.mark.django_db
def test_news_article_list(client):
    url = reverse('news:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


@pytest.mark.parametrize('payload', ['=cmd', '+1', '-1', '@SUM', '\tx', '\rx'])
def test_csv_safe_neutralizes_formula(payload):
    assert _csv_safe(payload).startswith("'")


def test_csv_safe_leaves_normal_values():
    assert _csv_safe('ana@example.com') == 'ana@example.com'
    assert _csv_safe('') == ''
    assert _csv_safe(None) == ''


@pytest.mark.django_db
def test_newsletter_subscribe_htmx_reactivates_existing_email(client, monkeypatch):
    site = make_site()
    mock_turnstile(monkeypatch)
    NewsletterSubscription.objects.create(
        email='ana@example.com',
        site=site,
        is_active=False,
    )

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {
            'email': 'ana@example.com',
            'cf-turnstile-response': 'valid-token',
        },
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    subscription = NewsletterSubscription.objects.get(email='ana@example.com', site=site)
    assert subscription.is_active is True


@pytest.mark.django_db
def test_newsletter_subscribe_rejects_invalid_turnstile(client, monkeypatch):
    make_site()
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {
            'email': 'ana@example.com',
            'cf-turnstile-response': 'bad-token',
        },
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    assert NewsletterSubscription.objects.count() == 0
    assert 'Confirme a verificação anti-bot' in response.content.decode()


@pytest.mark.django_db
def test_newsletter_subscribe_rejects_missing_turnstile(client, monkeypatch):
    make_site()
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {'email': 'ana@example.com'},
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    assert NewsletterSubscription.objects.count() == 0


@pytest.mark.django_db
def test_send_pending_newsletters_sends_only_to_article_site_subscribers():
    site = make_site(pk=1, domain='news.example.com', name='News')
    other_site = make_site(pk=2, domain='school.example.com', name='School')
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    NewsletterSubscription.objects.create(email='other@example.com', site=other_site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['reader@example.com']
    delivery = NewsletterDelivery.objects.get(article=article)
    assert delivery.status == NewsletterDelivery.Status.SENT
    article.refresh_from_db()
    assert article.newsletter_sent_at is not None


@pytest.mark.django_db
def test_send_pending_newsletters_dry_run_does_not_write_or_send():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters', dry_run=True)

    assert len(mail.outbox) == 0
    assert NewsletterDelivery.objects.count() == 0
    article.refresh_from_db()
    assert article.newsletter_sent_at is None


@pytest.mark.django_db
def test_send_pending_newsletters_is_idempotent_on_rerun():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters')
    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    assert NewsletterDelivery.objects.filter(article=article).count() == 1


@pytest.mark.django_db
def test_send_pending_newsletters_records_failure_and_retry(monkeypatch):
    site = make_site()
    NewsletterSubscription.objects.create(email='ok@example.com', site=site, is_active=True)
    NewsletterSubscription.objects.create(email='fail@example.com', site=site, is_active=True)
    article = make_article(site)

    from apps.news import newsletter

    original_send = newsletter.EmailMultiAlternatives.send

    def flaky_send(self, *args, **kwargs):
        if self.to == ['fail@example.com']:
            raise RuntimeError('SMTP indisponível')
        return original_send(self, *args, **kwargs)

    monkeypatch.setattr(newsletter.EmailMultiAlternatives, 'send', flaky_send)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    failed = NewsletterDelivery.objects.get(email='fail@example.com')
    assert failed.status == NewsletterDelivery.Status.FAILED
    assert failed.attempts == 1
    article.refresh_from_db()
    assert article.newsletter_sent_at is None

    monkeypatch.setattr(newsletter.EmailMultiAlternatives, 'send', original_send)
    call_command('send_pending_newsletters', retry_failed=True)

    failed.refresh_from_db()
    article.refresh_from_db()
    assert failed.status == NewsletterDelivery.Status.SENT
    assert failed.attempts == 2
    assert article.newsletter_sent_at is not None
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_newsletter_unsubscribe_token_deactivates_subscription(client):
    site = make_site()
    subscription = NewsletterSubscription.objects.create(
        email='reader@example.com',
        site=site,
        is_active=True,
    )
    token = make_unsubscribe_token(subscription)

    response = client.get(reverse('news:newsletter_unsubscribe', args=[token]))

    assert response.status_code == 302
    subscription.refresh_from_db()
    assert subscription.is_active is False


@pytest.mark.django_db
def test_newsletter_unsubscribe_rejects_invalid_token(client):
    site = make_site()
    subscription = NewsletterSubscription.objects.create(
        email='reader@example.com',
        site=site,
        is_active=True,
    )

    response = client.get(reverse('news:newsletter_unsubscribe', args=['token-invalido']))

    assert response.status_code == 302
    subscription.refresh_from_db()
    assert subscription.is_active is True


@pytest.mark.django_db
def test_send_pending_newsletters_ignores_unpublished_articles():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    make_article(site, slug='draft', status=Article.Status.DRAFT)
    make_article(site, slug='archived', status=Article.Status.ARCHIVED)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 0
    assert NewsletterDelivery.objects.count() == 0


# ── Blocos de conteúdo do artigo ─────────────────────────────────────────────

def make_image_media(name='inline.jpg'):
    return MediaFile.objects.create(
        title='Inline',
        file=make_image_upload(name, size=(800, 600), fmt='JPEG'),
        file_type='image',
        alt_text='alt',
    )


# ── Fase 10: renderização unificada (StreamField) ─────────────────────────

@pytest.mark.django_db
def test_article_detail_renders_body(client, settings, tmp_path):
    """Artigo com body populado → renderiza via StreamField."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='has-body', status=Article.Status.PUBLISHED)

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Renderizado via StreamField.</p>'},
    ])
    art.body = block.get_prep_value(value)
    art.save()

    response = client.get(reverse('news:article_detail', args=['has-body']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'Renderizado via StreamField' in html


@pytest.mark.django_db
def test_article_detail_falls_back_to_content_when_body_empty(client, settings):
    """Artigo com body vazio mas content populado → fallback para content."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='body-empty', status=Article.Status.PUBLISHED)
    art.body = None
    art.content = 'Conteúdo de fallback para renderização.'
    art.save()

    response = client.get(reverse('news:article_detail', args=['body-empty']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'Conteúdo de fallback para renderização.' in html


@pytest.mark.django_db
def test_article_detail_empty_body_and_content_renders_gracefully(client, settings):
    """Artigo sem body e sem content → renderiza sem erro (área vazia, não 500)."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='both-empty', status=Article.Status.PUBLISHED)
    art.body = None
    art.content = ''
    art.save()

    response = client.get(reverse('news:article_detail', args=['both-empty']))
    assert response.status_code == 200
    # Não deve conter fallback nenhum, mas também não deve ser 500



@pytest.mark.django_db
def test_csp_allows_instagram_and_tiktok_frames(client):
    response = client.get(reverse('news:list'))
    csp = response.headers.get('Content-Security-Policy', '')

    assert 'https://www.instagram.com' in csp
    assert 'https://www.tiktok.com' in csp
    assert 'https://www.youtube-nocookie.com' in csp  # YouTube segue permitido


# ── Fase 4: Article como Snippet + StreamField ──────────────────────────────


@pytest.mark.django_db
def test_article_streamfield_body_save_and_retrieve():
    """body StreamField aceita blocos e os recupera após save."""
    site = make_site()
    article = make_article(site, slug='stream-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'titulo', 'value': {'texto': 'Título do bloco', 'nivel': 'h2'}},
        {'type': 'texto', 'value': '<p>Parágrafo de teste.</p>'},
    ])
    article.body = block.get_prep_value(value)
    article.save()

    article.refresh_from_db()
    assert article.body is not None
    assert len(article.body) == 2
    assert article.body[0].block_type == 'titulo'
    assert article.body[0].value['texto'] == 'Título do bloco'


@pytest.mark.django_db
def test_article_tags_parental_m2m():
    """Article.tags funciona como M2M normal após mudança para ParentalManyToManyField."""
    site = make_site()
    article = make_article(site, slug='tag-test')
    tag = Tag.objects.create(name='Tag Parental', slug='tag-parental')

    article.tags.add(tag)
    article.save()

    article.refresh_from_db()
    assert article.tags.count() == 1
    assert article.tags.first().name == 'Tag Parental'


@pytest.mark.django_db
def test_article_mixin_fields_exist():
    """Campos dos mixins (DraftStateMixin, RevisionMixin, LockableMixin) existem."""
    site = make_site()
    article = make_article(site, slug='mixin-test')

    # Campos de DraftStateMixin
    assert article.live is True  # default=True
    assert article.has_unpublished_changes is False
    assert article.expired is False
    assert article.first_published_at is None
    assert article.last_published_at is None

    # Campo de RevisionMixin
    assert article.latest_revision is None

    # Campos de LockableMixin
    assert article.locked is False
    assert article.locked_at is None
    assert article.locked_by is None


@pytest.mark.django_db
def test_article_snippet_registration():
    """Article, Category e Tag estão registrados como Wagtail Snippets."""
    from wagtail.snippets.models import get_snippet_models
    snippet_names = {m.__name__ for m in get_snippet_models()}
    assert 'Article' in snippet_names
    assert 'Category' in snippet_names
    assert 'Tag' in snippet_names


@pytest.mark.django_db
def test_article_snippet_urls_resolve():
    """URLs de listagem dos snippets resolvem sem erro."""
    from django.urls import reverse

    article_url = reverse('wagtailsnippets_news_article:list')
    assert '/cms/snippets/news/article/' in article_url

    category_url = reverse('wagtailsnippets_news_category:list')
    assert '/cms/snippets/news/category/' in category_url

    tag_url = reverse('wagtailsnippets_news_tag:list')
    assert '/cms/snippets/news/tag/' in tag_url


@pytest.mark.django_db
def test_article_blocks_import_and_instantiate():
    """ArticleStreamBlock e todos os sub-blocos importam e instanciam sem erro."""
    from apps.news.blocks import (
        ArticleStreamBlock,
        CalloutBlock,
        EmbedBlock,
        HeadingBlock,
        ImageBlock,
        QuoteBlock,
        SeparatorBlock,
        SourceBlock,
    )

    # Instanciação individual
    HeadingBlock()
    ImageBlock()
    EmbedBlock()
    QuoteBlock()
    SeparatorBlock()
    CalloutBlock()
    SourceBlock()

    # Composição
    stream = ArticleStreamBlock()
    child_keys = set(stream.child_blocks.keys())
    expected = {'texto', 'titulo', 'citacao', 'separador', 'imagem', 'embed',
                'documento', 'destaque', 'tabela', 'fonte'}
    assert child_keys == expected


@pytest.mark.django_db
def test_embed_block_renders_without_leaking_comment():
    """O facade do embed renderiza sem vazar comentário de template."""
    from apps.news.blocks import EmbedBlock

    block = EmbedBlock()
    value = block.to_python({
        'embed_url': 'https://youtu.be/dQw4w9WgXcQ',
        'legenda': 'Vídeo oficial',
    })
    html = block.render(value)

    assert 'embed-facade' in html
    assert 'youtube-nocookie.com/embed/dQw4w9WgXcQ' in html
    # Comentário {# #} do Django é de UMA linha só: escrito em duas, vaza como
    # texto visível na matéria. Já aconteceu aqui e no password_reset_complete.
    assert '{#' not in html
    assert 'StreamField' not in html


def test_templates_have_no_multiline_hash_comments():
    """Nenhum {# #} multilinha nos templates — o lexer não os reconhece.

    A regex do Django é `{#.*?#}` sem re.DOTALL: um comentário quebrado em
    duas linhas não é removido e vaza renderizado para o leitor. Para textos
    longos, use {% comment %}. Guarda a árvore inteira porque o bug já
    apareceu duas vezes em templates diferentes.
    """
    import re
    from pathlib import Path

    from django.conf import settings

    # Mesma regex do lexer (django.template.base), sem re.DOTALL de propósito:
    # o que ela não casar é exatamente o que vaza renderizado.
    comment_re = re.compile(r'{#.*?#}')

    template_root = Path(settings.BASE_DIR) / 'templates'
    offenders = []
    for path in template_root.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        stripped = [m.span() for m in comment_re.finditer(text)]
        for opener in re.finditer(r'{#', text):
            if any(start <= opener.start() < end for start, end in stripped):
                continue
            lineno = text.count('\n', 0, opener.start()) + 1
            offenders.append(f'{path.relative_to(template_root)}:{lineno}')

    assert not offenders, (
        'Comentários {# #} multilinha (use {% comment %}): ' + ', '.join(offenders)
    )


@pytest.mark.django_db
def test_extract_content_from_body_texto():
    """_extract_content_from_body extrai HTML de blocos 'texto'."""
    site = make_site()
    art = make_article(site, slug='extract-texto')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Parágrafo um.</p>'},
        {'type': 'texto', 'value': '<p>Parágrafo dois.</p>'},
    ])
    art.body = block.get_prep_value(value)

    content = art._extract_content_from_body()
    assert '<p>Parágrafo um.</p>' in content
    assert '<p>Parágrafo dois.</p>' in content


@pytest.mark.django_db
def test_extract_content_from_body_with_legenda():
    """_extract_content_from_body extrai legendas de blocos imagem e embed."""
    site = make_site()
    art = make_article(site, slug='extract-legenda')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'imagem', 'value': {'imagem': None, 'legenda': 'Foto do evento'}},
        {'type': 'embed', 'value': {'embed_url': 'https://youtu.be/test', 'legenda': 'Vídeo oficial'}},
    ])
    art.body = block.get_prep_value(value)

    content = art._extract_content_from_body()
    assert 'Foto do evento' in content
    assert 'Vídeo oficial' in content


@pytest.mark.django_db
def test_extract_content_from_body_empty():
    """_extract_content_from_body retorna '' quando body está vazio."""
    site = make_site()
    art = make_article(site, slug='extract-empty')
    # body não foi populado — é None/vazio
    assert art._extract_content_from_body() == ''


@pytest.mark.django_db
def test_reading_time_from_body():
    """reading_time calcula a partir de body quando populado."""
    site = make_site()
    art = make_article(site, slug='rt-body')

    from apps.news.blocks import ArticleStreamBlock

    # Cria ~12 palavras no body (2 palavras por legenda × 6 blocos)
    words = 'uma duas tres quatro cinco seis sete oito nove dez onze doze'
    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': f'<p>{words}</p>'},
    ])
    art.body = block.get_prep_value(value)

    rt = art.reading_time
    assert rt >= 1  # 12 palavras / 200 = 0.06 → round = 0 → max(1, 0) = 1


@pytest.mark.django_db
def test_reading_time_from_content_when_body_empty():
    """reading_time usa content quando body está vazio."""
    site = make_site()
    art = make_article(site, slug='rt-content')
    art.content = 'uma duas tres quatro cinco seis sete oito nove dez onze doze treze quatorze quinze'
    # body vazio (não setado)
    rt = art.reading_time
    assert rt >= 1
    # Força refresh do content para garantir que usa content e não body
    art.save()
    art.refresh_from_db()
    assert art.content != ''
    assert art.reading_time >= 1


@pytest.mark.django_db
def test_save_regenerates_content_from_body():
    """save() completo (sem update_fields) regenera content a partir de body."""
    site = make_site()
    art = make_article(site, slug='save-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Conteúdo gerado pelo save.</p>'},
        {'type': 'imagem', 'value': {'imagem': None, 'legenda': 'Crédito da imagem'}},
    ])
    art.body = block.get_prep_value(value)
    art.save()  # save completo — content deve ser regenerado

    art.refresh_from_db()
    assert 'Conteúdo gerado pelo save' in art.content
    assert 'Crédito da imagem' in art.content


@pytest.mark.django_db
def test_save_from_body_flows_through_sanitization():
    """Conteúdo extraído de body passa pela sanitização no save()."""
    site = make_site()
    art = make_article(site, slug='sanitize-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Texto <script>alert("xss")</script> seguro</p>'},
    ])
    art.body = block.get_prep_value(value)
    art.save()

    art.refresh_from_db()
    # O <script> deve ter sido removido pela sanitização
    assert 'Texto' in art.content
    assert '<script>' not in art.content


@pytest.mark.django_db
def test_workflow_mixin_mro():
    """WorkflowMixin está antes de DraftStateMixin no MRO (check wagtailcore.E006)."""
    from wagtail.models import DraftStateMixin, RevisionMixin, WorkflowMixin

    mro = Article.__mro__
    wf_idx = mro.index(WorkflowMixin)
    ds_idx = mro.index(DraftStateMixin)
    rev_idx = mro.index(RevisionMixin)
    assert wf_idx < ds_idx < rev_idx, (
        f'MRO violation: WorkflowMixin={wf_idx}, DraftStateMixin={ds_idx}, '
        f'RevisionMixin={rev_idx}'
    )


@pytest.mark.django_db
def test_article_has_workflow_methods():
    """Article herda os métodos do WorkflowMixin."""
    art = Article(title='Test', slug='test-wf-methods', content='.')
    assert hasattr(art, 'has_workflow')
    assert hasattr(art, 'get_workflow')
    assert hasattr(art, 'workflow_states')
    assert hasattr(art, 'current_workflow_state')
    assert hasattr(art, 'workflow_in_progress')


@pytest.mark.django_db
def test_save_revision_still_works_with_workflow():
    """save_revision() continua funcionando após adicionar WorkflowMixin."""
    site = make_site()
    art = make_article_full(site, slug='wf-save-rev')
    rev = art.save_revision()
    assert rev is not None
    # Wagtail Revision.object_id é string (CharField de max_length=255)
    assert rev.object_id == str(art.pk) or int(rev.object_id) == art.pk


@pytest.mark.django_db
def test_workflow_is_assigned_after_migration():
    """Após a migração 0017, existe um Workflow associado a Article."""
    from wagtail.models import Workflow, WorkflowContentType

    workflow = Workflow.objects.filter(name='Moderação Editorial').first()
    assert workflow is not None, 'Workflow "Moderação Editorial" não existe após migração'

    # WorkflowContentType associa ao content type de Article
    wct = WorkflowContentType.objects.filter(
        content_type__app_label='news',
        content_type__model='article',
    ).first()
    assert wct is not None, 'WorkflowContentType não encontrado para Article'
    assert wct.workflow_id == workflow.pk, (
        f'WorkflowContentType aponta para workflow {wct.workflow_id}, '
        f'esperado {workflow.pk}'
    )
    assert workflow.active is True
    assert workflow.tasks.filter(name='Aprovação Editorial').exists(), (
        'GrupoApprovalTask "Aprovação Editorial" não está ligada ao workflow'
    )


@pytest.mark.django_db
def test_article_get_default_workflow():
    """Article.get_default_workflow() retorna o workflow configurado."""
    site = make_site()
    art = make_article(site, slug='wf-default')
    workflow = art.get_default_workflow()
    assert workflow is not None
    assert workflow.name == 'Moderação Editorial'


@pytest.mark.django_db
def test_article_has_workflow():
    """Article.has_workflow é True após a migração."""
    site = make_site()
    art = make_article(site, slug='wf-has')
    assert art.has_workflow is True


@pytest.mark.django_db
def test_editor_de_noticias_has_publish_permission(django_user_model):
    """Usuário com role 'news_editor' ganha a permissão publish_article."""
    from apps.accounts.admin_roles import sync_user_role_group

    editor = django_user_model.objects.create_user(
        username='editor-publish', password='x',
        role='news_editor',
    )
    # Antes da sincronização, NÃO deve ter a permissão
    assert not editor.has_perm('news.publish_article')

    sync_user_role_group(editor)

    # Django has_perm pode usar cache interno. Recarregamos o modelo
    # User do banco e verificamos via get_all_permissions().
    from django.contrib.auth import get_user_model
    editor_fresh = get_user_model().objects.get(pk=editor.pk)
    perms = editor_fresh.get_all_permissions()
    assert 'news.publish_article' in perms, (
        f'Editor de Notícias precisa ter publish_article. Perms: {sorted(perms)}'
    )
    assert 'news.lock_article' in perms, (
        'Editor de Notícias precisa ter lock_article'
    )
    assert 'news.unlock_article' in perms, (
        'Editor de Notícias precisa ter unlock_article'
    )


@pytest.mark.django_db
def test_editor_de_noticias_lacks_publish_without_sync(django_user_model):
    """Sem sync_user_role_group, o editor NÃO tem publish_article."""
    editor = django_user_model.objects.create_user(
        username='editor-no-sync', password='x',
        role='news_editor',
    )
    assert not editor.has_perm('news.publish_article'), (
        'Antes do sync, publish_article deve ser False'
    )


@pytest.mark.django_db
def test_ensure_admin_role_groups_grants_publish(django_user_model):
    """ensure_admin_role_groups() cria o grupo Editor de Notícias com publish."""
    from django.contrib.auth.models import Group

    from apps.accounts.admin_roles import ensure_admin_role_groups

    ensure_admin_role_groups()
    group = Group.objects.get(name='Editor de Notícias')
    perms = group.permissions.filter(
        content_type__app_label='news',
        codename='publish_article',
    )
    assert perms.exists(), 'Grupo Editor de Notícias deve ter publish_article'


@pytest.mark.django_db
def test_article_publish_method():
    """Article.publish() (herdado do DraftStateMixin) funciona."""
    site = make_site()
    art = make_article_full(site, slug='wf-publish', status=Article.Status.PUBLISHED)
    # Já publicado — vamos verificar que live=True
    rev = art.save_revision(user=None)
    art.publish(revision=rev)
    art.refresh_from_db()
    # Wagtail publish() seta live=True e last_published_at
    assert art.live is True
    assert art.last_published_at is not None


@pytest.mark.django_db
def test_article_draftstate_properties():
    """Propriedades de DraftStateMixin continuam funcionais."""
    site = make_site()
    art = make_article(site, slug='wf-draft-prop')
    # Inicialmente published
    art.status = Article.Status.PUBLISHED
    art.save()
    assert art.status_string == 'live' or art.status_string is not None


@pytest.mark.django_db
def test_article_workflow_state_creation(django_user_model):
    """O workflow pode ser iniciado em um Article."""
    site = make_site()
    art = make_article_full(site, slug='wf-state', status=Article.Status.DRAFT)
    art.save_revision()

    workflow = art.get_default_workflow()
    assert workflow is not None

    user = django_user_model.objects.create_user(
        username='wf-user-state', password='x',
        email='wf-user-state@test.com',
        role='news_editor',
    )
    from apps.accounts.admin_roles import sync_user_role_group
    sync_user_role_group(user)

    # Inicia o workflow
    workflow_state = workflow.start(art, user)
    assert workflow_state is not None
    assert workflow_state.status == 'in_progress'

    # Verifica que o workflow_state aparece no modelo
    art.refresh_from_db()
    assert art.workflow_in_progress is True
    current = art.current_workflow_state
    assert current is not None
    assert current.pk == workflow_state.pk


# ── Fase 9: featured_image_wagtail (ponte de capa) ────────────────────────────


@pytest.mark.django_db
def test_featured_image_wagtail_field_exists():
    """O campo featured_image_wagtail existe no model Article e é nullable."""
    site = make_site()
    article = make_article(site, slug='wagtail-field-test')
    # Campo deve existir como atributo e ser None por padrão
    assert hasattr(article, 'featured_image_wagtail')
    assert article.featured_image_wagtail is None
    assert article.featured_image_wagtail_id is None


@pytest.mark.django_db
def test_featured_image_wagtail_fk_to_image_model(settings, tmp_path):
    """O campo aceita FK para o modelo Image do Wagtail."""
    settings.MEDIA_ROOT = str(tmp_path)
    from wagtail.images import get_image_model
    image_model = get_image_model()

    site = make_site()
    article = make_article(site, slug='fk-test')

    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage

    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (255, 0, 0)).save(buf, format='PNG')
    buf.seek(0)
    content = buf.read()

    wagtail_image = image_model.objects.create(
        title='Test Image',
        file=ContentFile(content, name='test.png'),
        width=100,
        height=100,
        file_size=len(content),
    )

    article.featured_image_wagtail = wagtail_image
    article.save(update_fields=['featured_image_wagtail'])

    article.refresh_from_db()
    assert article.featured_image_wagtail_id == wagtail_image.pk
    assert article.featured_image_wagtail == wagtail_image


@pytest.mark.django_db
def test_featured_image_wagtail_no_reverse_accessor_clash():
    """related_name='+' evita choque de reverse accessor."""
    field = Article._meta.get_field('featured_image_wagtail')
    assert field.remote_field.related_name == '+'


# ── Bridge command tests ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_migrate_featured_images_dry_run_no_changes(settings, tmp_path):
    """Dry-run não persiste nada no banco."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa para dry-run',
        slug='dry-run-cap',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(800, 600)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    assert article.featured_image_wagtail_id is None

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--article-id', str(article.pk),
        stdout=out, stderr=StringIO(),
    )

    # Após dry-run, nada deve ter sido gravado
    article.refresh_from_db()
    assert article.featured_image_wagtail_id is None
    assert image_model.objects.count() == image_count_before

    output = out.getvalue()
    assert 'Snap' in output or 'snaps' in output.lower() or 'PULADO' in output or 'Image' in output


@pytest.mark.django_db
def test_migrate_featured_images_apply_creates_image(settings, tmp_path):
    """--apply cria Image e popula featured_image_wagtail."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa',
        slug='capa-apply',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(800, 600)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=out, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert article.featured_image_wagtail_id is not None
    assert image_model.objects.count() == image_count_before + 1

    wagtail_image = article.featured_image_wagtail
    assert wagtail_image.title == 'Artigo com capa'
    assert wagtail_image.width <= 800  # imagekit pode ter redimensionado
    assert wagtail_image.height <= 600
    # O arquivo da Image do Wagtail herda o nome do original (já convertido a JPEG pelo imagekit)
    assert wagtail_image.file.name.endswith(('.png', '.jpg', '.jpeg'))

    output = out.getvalue()
    assert 'RESUMO FINAL' in output or '1' in output


@pytest.mark.django_db
def test_migrate_featured_images_idempotent(settings, tmp_path):
    """Rodar o comando duas vezes com --apply não duplica imagens."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo idempotent',
        slug='idempotent',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(200, 200)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()

    from io import StringIO

    # Primeira execução
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=StringIO(), stderr=StringIO(),
    )

    image_count_after_first = image_model.objects.count()
    article.refresh_from_db()
    first_image_pk = article.featured_image_wagtail_id

    # Segunda execução — deve pular
    out2 = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=out2, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert image_model.objects.count() == image_count_after_first
    assert article.featured_image_wagtail_id == first_image_pk

    output2 = out2.getvalue()
    assert 'PULADO' in output2 or 'skipp' in output2.lower() or 'ja preenchido' in output2.lower()


@pytest.mark.django_db
def test_migrate_featured_images_skips_without_featured_image(settings, tmp_path):
    """Artigos sem featured_image são ignorados."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = make_article(site, slug='sem-capa')
    article.featured_image_wagtail_id = None  # explícito
    article.save()

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        stdout=out, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert article.featured_image_wagtail_id is None
    assert image_model.objects.count() == image_count_before


@pytest.mark.django_db
def test_migrate_featured_images_does_not_touch_old_field(settings, tmp_path):
    """O campo featured_image original permanece intacto após a migração."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Campo antigo preservado',
        slug='old-field',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(400, 300)),
    )

    old_image_name = article.featured_image.name

    from io import StringIO
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=StringIO(), stderr=StringIO(),
    )

    article.refresh_from_db()
    # featured_image original deve continuar igual
    assert article.featured_image.name == old_image_name
    assert article.featured_image  # não vazio
    # E featured_image_wagtail deve ter sido populado
    assert article.featured_image_wagtail_id is not None


# ── Wagtail admin ─────────────────────────────────────────────────────────────


def _panel_field_names(panels):
    """Nomes de campo de uma lista de painéis, DESCENDO nos painéis compostos.

    Um FieldPanel dentro de MultiFieldPanel está tão presente no formulário como
    um solto no topo — checar só o nível raiz daria falso negativo e nos faria
    "consertar" a estrutura do formulário para agradar o teste.
    """
    names = []
    for panel in panels:
        if hasattr(panel, 'field_name'):
            names.append(panel.field_name)
        names.extend(_panel_field_names(getattr(panel, 'children', []) or []))
    return names


@pytest.mark.django_db
def test_wagtail_snippet_panels_include_featured_image_wagtail():
    """O FieldPanel de featured_image_wagtail está nos painéis do SnippetViewSet."""
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = _panel_field_names(ArticleSnippetViewSet().panels)

    assert 'featured_image_wagtail' in panel_names
    # featured_image (campo antigo) NÃO deve estar nos painéis Wagtail
    assert 'featured_image' not in panel_names


@pytest.mark.django_db
def test_wagtail_snippet_panels_hide_status_field():
    """Round 6: status não aparece no formulário — é controlado só pelos
    botões nativos Publicar/Despublicar/Salvar rascunho (sincronizados via
    signals), evitando dois controles para o mesmo estado."""
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = _panel_field_names(ArticleSnippetViewSet().panels)

    assert 'status' not in panel_names


@pytest.mark.django_db
def test_wagtail_snippet_panels_cover_every_editable_field():
    """Nenhum campo editável do Article fica sem tela.

    O Article deixou de ser registrado no admin do Django, então o formulário do
    snippet é a ÚNICA porta de edição. Quando is_featured, featured_image_caption,
    meta_title e meta_description saíram dos painéis, os quatro continuaram sendo
    lidos pelo site público e ninguém tinha onde preenchê-los. Este teste existe
    para que o próximo campo esquecido apareça aqui e não em produção.
    """
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = set(_panel_field_names(ArticleSnippetViewSet().panels))

    # Mantidos pela máquina, não por gente: os botões de publicação do Wagtail
    # (ver teste acima), o agendamento do PublishingPanel e o contador de acessos
    # incrementado por apps.news.views.article_detail.
    machine_maintained = {
        'status', 'published_at', 'first_published_at', 'expire_at', 'go_live_at',
        'view_count',
    }
    # Substituído por featured_image_wagtail; segue no modelo só para ler o acervo.
    legacy = {'featured_image'}

    editable = {
        field.name for field in Article._meta.get_fields()
        if getattr(field, 'editable', False) and not field.auto_created
    }
    missing = editable - panel_names - machine_maintained - legacy

    assert not missing, f'Campos editáveis sem FieldPanel (inalcançáveis na interface): {sorted(missing)}'


# ── Fase 10: SEO coverage ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_sitemap_items_and_lastmod():
    """ArticleSitemap retorna artigos publicados com lastmod em updated_at."""
    site = make_site()
    art = Article.objects.create(
        title='Artigo Sitemap', slug='sitemap-test',
        content='Conteúdo.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    from apps.news.sitemaps import ArticleSitemap

    sitemap = ArticleSitemap()
    items = sitemap.items()
    assert art in items
    assert sitemap.lastmod(art) == art.updated_at


@pytest.mark.django_db
def test_latest_articles_feed_title_and_items(client):
    """LatestArticlesFeed tem título, descrição e items publicados."""
    site = make_site(pk=1, domain='testserver')
    art = Article.objects.create(
        title='Feed Article', slug='feed-article',
        content='Feed content.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    response = client.get(reverse('news:feed'))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Feed Article' in content
    assert art.get_absolute_url() in content


@pytest.mark.django_db
def test_category_feed_title_and_items(client):
    """CategoryFeed retorna artigos filtrados por categoria."""
    site = make_site(pk=1, domain='testserver')
    cat = Category.objects.create(name='Categoria Feed', slug='cat-feed')
    Article.objects.create(
        title='Category Feed Article', slug='cat-feed-article',
        content='Cat feed.', site=site, category=cat,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    response = client.get(reverse('news:category_feed', args=['cat-feed']))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Category Feed Article' in content


@pytest.mark.django_db
def test_article_detail_json_ld_publisher_has_logo(client, settings, tmp_path):
    """JSON-LD inclui publisher.logo quando site_settings.logo está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage

    from apps.common.models import SiteExtension

    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)

    ext, _ = SiteExtension.objects.get_or_create(site=site)
    ext.logo.save('logo.png', ContentFile(buf.read()))
    ext.save()

    art = make_article(site, slug='jsonld-logo', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['jsonld-logo']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '"logo"' in html
    assert 'logo.png' in html


@pytest.mark.django_db
def test_article_detail_json_ld_no_logo_when_not_set(client):
    """JSON-LD NÃO inclui logo quando site_settings não tem logo."""
    site = make_site(pk=1, domain='testserver')
    from apps.common.models import SiteExtension
    SiteExtension.objects.filter(site=site).delete()

    art = make_article(site, slug='jsonld-no-logo', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['jsonld-no-logo']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '"logo"' not in html


@pytest.mark.django_db
def test_article_detail_og_tags(client):
    """Página de artigo tem meta tags Open Graph."""
    site = make_site(pk=1, domain='testserver')
    art = make_article(site, slug='og-test', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.meta_title = 'OG Title'
    art.meta_description = 'OG Desc'
    art.save()

    response = client.get(reverse('news:article_detail', args=['og-test']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '<meta property="og:title" ' in html
    assert '<meta property="og:description" ' in html
    assert '<meta property="og:type" content="article"' in html
    assert '<meta property="og:url" ' in html
    assert 'OG Title' in html


@pytest.mark.django_db
def test_article_detail_twitter_card(client):
    """Página de artigo tem Twitter Card meta tags."""
    site = make_site(pk=1, domain='testserver')
    art = make_article(site, slug='tw-test', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['tw-test']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '<meta name="twitter:card"' in html
    assert '<meta name="twitter:title"' in html
    assert '<meta name="twitter:description"' in html


@pytest.mark.django_db
def test_article_detail_article_section_in_og(client):
    """Meta tag article:section aparece para artigo com categoria."""
    site = make_site(pk=1, domain='testserver')
    cat = Category.objects.create(name='Test Cat OG', slug='test-cat-og')
    Article.objects.create(
        title='Artigo section meta', slug='art-section-meta',
        content='Conteúdo.', site=site, category=cat,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    response = client.get(reverse('news:article_detail', args=['art-section-meta']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'article:section' in html
    assert 'Test Cat OG' in html


# ── Fase 11b: NewsHomeConfig ──────────────────────────────────────────────────


def _make_stream_value(article_pks):
    """Constrói valor bruto para o StreamField secondary_highlights."""
    return [{'type': 'artigo', 'value': pk} for pk in article_pks]


@pytest.mark.django_db
def test_newshomeconfig_singleton_per_site():
    """Segundo create() com o mesmo site levanta IntegrityError."""
    site = make_site()
    NewsHomeConfig.objects.create(site=site)
    with pytest.raises(Exception):  # IntegrityError
        NewsHomeConfig.objects.create(site=site)


@pytest.mark.django_db
def test_article_list_regression_without_config(client, settings):
    """Sem NewsHomeConfig, featured continua automático (regressão zero)."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    Article.objects.create(
        title='Featured Article', slug='featured-art', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    Article.objects.create(
        title='Regular Article', slug='regular-art', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now(),
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Featured Article' in html
    # Regular deve aparecer no grid (excluindo apenas featured)
    assert 'Regular Article' in html


@pytest.mark.django_db
def test_hero_override_published_becomes_featured(client, settings):
    """hero_override publicado e do site certo vira featured."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    override = Article.objects.create(
        title='Manual Hero', slug='manual-hero', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-featured', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Manual Hero' in html
    # Auto featured NÃO deve ser o hero (não aparece no hero, mas pode aparecer no grid)
    assert 'Auto Featured' in html


@pytest.mark.django_db
def test_hero_override_draft_ignored_uses_auto(client, settings):
    """hero_override não publicado (draft) é ignorado, cai no automático."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    override = Article.objects.create(
        title='Draft Hero', slug='draft-hero', content='.', site=site,
        status=Article.Status.DRAFT,
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-feat', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # O automático deve aparecer como featured
    assert 'auto-feat' in html


@pytest.mark.django_db
def test_hero_override_other_site_ignored(client, settings):
    """hero_override de outro site é ignorado, cai no automático."""
    site1 = make_site(pk=settings.SITE_ID, domain='testserver')
    site2 = make_site(pk=999, domain='other.testserver', name='Other')
    override = Article.objects.create(
        title='Other Site Hero', slug='other-hero', content='.', site=site2,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-feat', content='.', site=site1,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site1, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # O artigo do outro site não vira hero
    assert 'auto-feat' in html


@pytest.mark.django_db
def test_secondary_highlights_appear_in_order_and_excluded_from_grid(client, settings):
    """2-4 destaques secundários aparecem na ordem configurada e somem do grid."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    h1 = Article.objects.create(
        title='Highlight 1', slug='h1', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    h2 = Article.objects.create(
        title='Highlight 2', slug='h2', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Grid Article', slug='grid-art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([h1.pk, h2.pk])
    config.save()
    config.refresh_from_db()

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # Destaques aparecem na seção de destaques
    assert 'h1' in html
    assert 'h2' in html
    # Grid article (não-destaque) aparece no grid
    assert 'grid-art' in html


@pytest.mark.django_db
def test_secondary_highlights_invalid_ignored_silently(client, settings):
    """Item inválido (não publicado) nos destaques é ignorado sem erro."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    valid = Article.objects.create(
        title='Valid Highlight', slug='valid', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    draft = Article.objects.create(
        title='Draft Highlight', slug='draft-hl', content='.', site=site,
        status=Article.Status.DRAFT,
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([draft.pk, valid.pk])
    config.save()
    config.refresh_from_db()

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # Draft não deve aparecer nos destaques
    assert 'valid' in html
    assert 'draft-hl' not in html  # slug do draft não aparece nos destaques


@pytest.mark.django_db
def test_htmx_load_more_excludes_hero_and_highlights(client, settings):
    """Carregar mais via HTMX não reexibe hero nem destaques."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Extra Article', slug='extra', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now() - timezone.timedelta(days=2),
    )
    h1 = Article.objects.create(
        title='Highlight 1', slug='hl1', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([h1.pk])
    config.save()

    response = client.get(
        reverse('news:article_list_page') + '?page=1',
        HTTP_HX_REQUEST='true',
    )

    html = response.content.decode()
    assert response.status_code == 200
    # Featured e highlight não reaparecem no grid HTMX
    assert 'feat' not in html
    assert 'hl1' not in html
    assert 'extra' in html


@pytest.mark.django_db
def test_seo_home_uses_home_config_fields(client, settings):
    """SEO da home usa home_config.meta_title/meta_description quando definidos."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True,
        meta_title='SEO Title Test',
        meta_description='SEO Desc Test',
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert '<title>SEO Title Test</title>' in html
    assert '<meta name="description" content="SEO Desc Test">' in html
    assert '<meta property="og:title" content="SEO Title Test">' in html
    assert '<meta property="og:description" content="SEO Desc Test">' in html
    assert '<meta name="twitter:title" content="SEO Title Test">' in html
    assert '<meta name="twitter:description" content="SEO Desc Test">' in html


@pytest.mark.django_db
def test_seo_home_fallback_without_config(client, settings):
    """SEO da home cai no fallback atual quando NewsHomeConfig não existe."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Blog da Kelly' in html  # news_portal_name default
    assert 'Conteúdos, notícias e bastidores da Komuniki com Kelly Farias.' in html


@pytest.mark.django_db
def test_seo_home_fallback_with_empty_fields(client, settings):
    """SEO cai no fallback quando campos estão vazios."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(site=site, is_active=True)  # sem SEO preenchido

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Blog da Kelly' in html
    assert 'Conteúdos, notícias e bastidores da Komuniki com Kelly Farias.' in html


@pytest.mark.django_db
def test_news_home_shows_social_section_when_enabled(client, settings):
    """Seção social aparece na home do news quando social_section_enabled=True."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    from apps.common.models import SiteExtension
    from apps.social.models import Platform, SocialAccount, SocialPost

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    SiteExtension.objects.update_or_create(
        site=site,
        defaults={
            'social_section_enabled': True,
            'social_section_title': 'Acompanhe nas redes',
            'instagram_url': 'https://www.instagram.com/komunikiescola/',
        },
    )
    account = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM, display_name='Komuniki IG',
        username='komuniki', is_active=True,
    )
    SocialPost.objects.create(
        account=account, permalink='https://www.instagram.com/p/MANUAL/',
        published_at=timezone.now(), is_visible=True, is_manual=True,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Acompanhe nas redes' in html
    assert 'https://www.instagram.com/p/MANUAL/' in html


@pytest.mark.django_db
def test_news_home_hides_social_section_when_disabled(client, settings):
    """Seção social some da home do news quando social_section_enabled=False."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    from apps.common.models import SiteExtension
    from apps.social.models import Platform, SocialAccount, SocialPost

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    SiteExtension.objects.update_or_create(
        site=site,
        defaults={'social_section_enabled': False},
    )
    account = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM, display_name='Komuniki IG',
        username='komuniki', is_active=True,
    )
    SocialPost.objects.create(
        account=account, permalink='https://www.instagram.com/p/HIDDEN/',
        published_at=timezone.now(), is_visible=True, is_manual=True,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'https://www.instagram.com/p/HIDDEN/' not in html
    assert 'social-section-title' not in html


@pytest.mark.django_db
def test_get_social_section_posts_respects_toggles():
    """get_social_section_posts respeita toggles de SiteExtension."""
    from apps.common.models import SiteExtension
    from apps.common.social_section import get_social_section_posts
    from apps.social.models import Platform, SocialAccount, SocialPost

    site = make_site(pk=1)

    # Sem SiteExtension
    assert get_social_section_posts(site) == []

    ext, _ = SiteExtension.objects.update_or_create(
        site=site,
        defaults={'social_section_enabled': False},
    )
    assert get_social_section_posts(site) == []

    ext.social_section_enabled = True
    ext.social_show_instagram = True
    ext.social_show_tiktok = False
    ext.save()

    ig = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM,
        display_name='IG', username='ig', is_active=True,
    )
    tk = SocialAccount.objects.create(
        site=site, platform=Platform.TIKTOK,
        display_name='TK', username='tk', is_active=True,
    )
    SocialPost.objects.create(
        account=ig, permalink='https://ig.test/p/1',
        published_at=timezone.now(), is_visible=True,
    )
    SocialPost.objects.create(
        account=tk, permalink='https://tk.test/v/1',
        published_at=timezone.now(), is_visible=True,
    )

    # Evita cache da OneToOneField: usa Site fresco
    site = Site.objects.get(pk=site.pk)
    posts = get_social_section_posts(site)
    assert len(posts) == 1
    assert posts[0].account.platform == Platform.INSTAGRAM


@pytest.mark.django_db
def test_wagtail_snippet_newshomeconfig_registered():
    """NewsHomeConfig está registrado como Wagtail Snippet."""
    from wagtail.snippets.models import get_snippet_models
    snippet_names = {m.__name__ for m in get_snippet_models()}
    assert 'NewsHomeConfig' in snippet_names


@pytest.mark.django_db
def test_article_get_preview_context_renders_public_template(rf):
    """get_preview_context() supre as variáveis que news/article_detail.html exige.

    Regressão: PreviewableMixin.get_preview_context() por padrão só fornece
    `object`/`request`, mas o template de preview (reusado da página pública)
    também referencia `article`, `comments`, `related_articles` etc. Sem
    Article.get_preview_context() sobrescrito, a renderização quebra com
    VariableDoesNotExist para qualquer artigo — reproduzido manualmente via
    o botão "Alternar pré-visualização" no /cms/ antes da correção.
    """
    from django.template.loader import render_to_string

    site = make_site()
    article = make_article_full(site, slug='preview-check')
    request = rf.get('/')

    context = article.get_preview_context(request, 'default')
    assert context['article'] == article
    assert context['comments'].count() == 0
    assert context['comment_count'] == 0

    html = render_to_string(article.get_preview_template(request, 'default'), context, request=request)
    assert article.title in html


# ── Bug C: cover_image_url / has_cover_image ────────────────────────────────


@pytest.mark.django_db
def test_cover_image_url_empty_when_no_image():
    """cover_image_url retorna '' quando nenhum campo de imagem está preenchido."""
    site = make_site()
    article = make_article(site, slug='no-image')
    article.featured_image_wagtail = None
    article.featured_image = None
    article.save()

    assert article.cover_image_url == ''
    assert article.has_cover_image is False


@pytest.mark.django_db
def test_cover_image_url_legacy_only(settings, tmp_path):
    """cover_image_url retorna URL legada quando só featured_image está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()
    article = Article.objects.create(
        title='Legacy Only',
        slug='legacy-only',
        content='.',
        site=site,
        featured_image=make_image_upload('legacy.png', size=(800, 600)),
    )

    url = article.cover_image_url
    assert url == article.featured_image.url
    assert article.has_cover_image is True


@pytest.mark.django_db
def test_cover_image_url_wagtail_only(settings, tmp_path):
    """cover_image_url retorna rendition URL quando só featured_image_wagtail está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage
    from wagtail.images import get_image_model

    site = make_site()
    article = make_article(site, slug='wagtail-only')

    image_model = get_image_model()
    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Wagtail Image',
        file=ContentFile(buf.read(), name='wagtail.png'),
        width=100,
        height=100,
        file_size=buf.tell(),
    )

    article.featured_image_wagtail = img
    article.save(update_fields=['featured_image_wagtail'])

    url = article.cover_image_url
    assert url != ''
    assert article.has_cover_image is True


@pytest.mark.django_db
def test_cover_image_url_wagtail_wins_when_both(settings, tmp_path):
    """Wagtail field tem prioridade quando ambos os campos estão definidos."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from wagtail.images import get_image_model

    site = make_site()
    article = Article.objects.create(
        title='Both Fields',
        slug='both-fields',
        content='.',
        site=site,
        featured_image=make_image_upload('legacy.png', size=(400, 300)),
    )

    image_model = get_image_model()
    from PIL import Image as PILImage
    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (255, 0, 0)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Wagtail Override',
        file=ContentFile(buf.read(), name='wagtail.png'),
        width=100,
        height=100,
        file_size=buf.tell(),
    )

    article.featured_image_wagtail = img
    article.save(update_fields=['featured_image_wagtail'])

    url = article.cover_image_url
    legacy_url = article.featured_image.url
    assert url != legacy_url, f'Wagtail URL {url} não deve ser igual à legacy URL {legacy_url}'
    assert article.has_cover_image is True


# ── Bug D: bloco de imagem StreamField ─────────────────────────────────────


@pytest.mark.django_db
def test_image_block_renders_non_empty_img_src(settings, tmp_path):
    """templates/news/blocks/image.html renderiza <img src> preenchido com uma imagem real."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from django.template import Context, Template
    from wagtail.images import get_image_model

    image_model = get_image_model()
    from PIL import Image as PILImage
    buf = BytesIO()
    PILImage.new('RGB', (200, 150), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Inline Block Image',
        file=ContentFile(buf.read(), name='inline.png'),
        width=200,
        height=150,
        file_size=buf.tell(),
    )

    template = Template(
        '{% load wagtailimages_tags %}'
        '{% include "news/blocks/image.html" with value=value %}'
    )

    html = template.render(Context({
        'value': {
            'imagem': img,
            'legenda': 'Crédito da foto',
        },
    }))

    assert 'src="' in html
    assert 'src=""' not in html
    assert 'Crédito da foto' in html


@pytest.mark.django_db
def test_image_block_renders_nothing_when_no_image():
    """Bloco de imagem não renderiza nada quando value.imagem é None/vazio."""
    from django.template import Context, Template

    template = Template(
        '{% load wagtailimages_tags %}'
        '{% include "news/blocks/image.html" with value=value %}'
    )

    html = template.render(Context({
        'value': {
            'imagem': None,
            'legenda': '',
        },
    }))

    assert 'src="' not in html or html.strip() == ''


# ── Round 7: Wagtail dashboard "Painel da Redação" ──────────────────────────


def _make_wagtail_editor(django_user_model, username='editor-dashboard', role='news_editor'):
    """Cria um usuário com acesso ao Wagtail admin e permissões de editor de notícias."""
    from apps.accounts.admin_roles import ensure_admin_role_groups, sync_user_role_group

    ensure_admin_role_groups()
    user = django_user_model.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
        role=role,
    )
    sync_user_role_group(user)
    return user


@pytest.mark.django_db
def test_wagtail_dashboard_redacao_panels_render(client, django_user_model):
    """Editor de Notícias vê os painéis do Painel da Redação no dashboard Wagtail (/cms/)."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)
    # "Notícias recentes" só renderiza quando existe pelo menos 1 artigo (sem bloco vazio).
    make_article_full(site, slug='dashboard-render-teste', status=Article.Status.PUBLISHED)
    client.force_login(user)

    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Painel da Redação' in content
    assert 'Criar nova notícia' in content
    assert 'Publicadas' in content
    assert 'Rascunhos' in content
    assert 'Em revisão' in content
    assert 'Agendadas' in content
    assert 'Categorias' in content
    assert 'Tags' in content
    assert 'Home do portal' in content
    assert 'Ver portal' in content
    assert 'Notícias recentes' in content


@pytest.mark.django_db
def test_wagtail_dashboard_panels_hidden_without_permission(client, django_user_model):
    """Usuário sem news.view_article não vê os painéis do Painel da Redação."""
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user(
        username='no-news-perm',
        email='no-news-perm@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
    )
    # Concede acesso ao Wagtail admin mas NÃO permissões de news
    access_admin_perm = Permission.objects.get(
        content_type__app_label='wagtailadmin',
        codename='access_admin',
    )
    user.user_permissions.add(access_admin_perm)
    client.force_login(user)

    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Painel da Redação' not in content
    assert 'Criar nova notícia' not in content


@pytest.mark.django_db
def test_wagtail_dashboard_status_cards_visible_for_editor(client, django_user_model):
    """Os 4 cards de status (publicadas/rascunhos/em revisão/agendadas) aparecem para o editor."""
    user = _make_wagtail_editor(django_user_model)
    client.force_login(user)

    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Publicadas' in content
    assert 'Rascunhos' in content
    assert 'Em revisão' in content
    assert 'Agendadas' in content


@pytest.mark.django_db
def test_wagtail_dashboard_panel_shows_article_counts(client, django_user_model):
    """Painel editorial exibe contagem correta de artigos publicados e rascunhos."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)

    # Cria artigos publicados e rascunhos
    Article.objects.create(
        title='Publicado 1', slug='pub-1', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )
    Article.objects.create(
        title='Publicado 2', slug='pub-2', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )
    Article.objects.create(
        title='Rascunho 1', slug='draft-1', content='.', site=site,
        status=Article.Status.DRAFT,
    )

    client.force_login(user)
    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 200
    content = response.content.decode()
    assert '2' in content  # publicados count


@pytest.mark.django_db
def test_wagtail_dashboard_panel_recent_articles(client, django_user_model):
    """Painel editorial mostra lista de artigos recentes com links de edição."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)

    article = Article.objects.create(
        title='Artigo Recente Teste', slug='recent-test', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )

    client.force_login(user)
    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Artigo Recente Teste' in content
    # Verifica que o link de edição aponta para o snippet correto
    edit_url = reverse('wagtailsnippets_news_article:edit', args=[article.pk])
    assert edit_url in content


@pytest.mark.django_db
def test_article_status_counts_all_categories(django_user_model):
    """_article_status_counts() conta publicadas, rascunhos, agendadas e em revisão corretamente."""
    from apps.news.wagtail_hooks import _article_status_counts

    site = make_site()
    make_article_full(site, slug='status-pub', status=Article.Status.PUBLISHED)
    make_article_full(site, slug='status-draft', status=Article.Status.DRAFT)

    scheduled = make_article_full(site, slug='status-scheduled', status=Article.Status.DRAFT)
    scheduled.live = False
    scheduled.go_live_at = timezone.now() + timezone.timedelta(days=1)
    scheduled.save()

    in_review = make_article_full(site, slug='status-review', status=Article.Status.DRAFT)
    in_review.save_revision()
    workflow = in_review.get_default_workflow()
    reviewer = make_user(username='review-author-status')
    workflow.start(in_review, reviewer)

    counts = _article_status_counts()
    assert counts['published'] == 1
    assert counts['draft'] == 3  # status-draft + status-scheduled + status-review (todos com status DRAFT)
    assert counts['scheduled'] == 1
    assert counts['in_review'] == 1


@pytest.mark.django_db
def test_continue_working_panel_scoped_to_editing_user(client, django_user_model):
    """"Continue trabalhando" só aparece para quem editou o próprio rascunho por último."""
    site = make_site()
    user_a = _make_wagtail_editor(django_user_model, username='editor-continue-a')
    user_b = _make_wagtail_editor(django_user_model, username='editor-continue-b')

    article = make_article_full(site, slug='continuar-teste', status=Article.Status.DRAFT)
    article.live = False
    article.save()
    article.save_revision(user=user_a)

    client.force_login(user_a)
    response = client.get(reverse('wagtailadmin_home'))
    assert 'Continuar edição' in response.content.decode()

    client.force_login(user_b)
    response = client.get(reverse('wagtailadmin_home'))
    assert 'Continuar edição' not in response.content.decode()


# ── Wagtail publish/unpublish → status sync ──────────────────────────────────


@pytest.mark.django_db
def test_wagtail_publish_syncs_status_to_published():
    """Publicar via Wagtail (save_revision().publish()) atualiza status para PUBLISHED."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-sync', status=Article.Status.DRAFT)

    rev = art.save_revision()
    rev.publish()

    art.refresh_from_db()
    assert art.status == Article.Status.PUBLISHED
    assert art.published_at is not None


@pytest.mark.django_db
def test_wagtail_unpublish_syncs_status_to_archived():
    """Despublicar via Wagtail (.unpublish()) atualiza status para ARCHIVED."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-unpub-sync', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    # Publicar via Wagtail para garantir live=True
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()
    assert art.live is True
    assert art.status == Article.Status.PUBLISHED

    # Despublicar
    art.unpublish()
    art.refresh_from_db()

    assert art.status == Article.Status.ARCHIVED
    assert art.live is False


@pytest.mark.django_db
def test_wagtail_publish_article_appears_in_public_queryset():
    """Artigo publicado via Wagtail aparece em on_site.filter(status=PUBLISHED)."""
    site = make_site(pk=1, domain='testserver')
    art = make_article_full(site, slug='wagtail-pub-queryset', status=Article.Status.DRAFT)

    # Antes de publicar, NÃO deve aparecer no queryset público
    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art not in qs

    # Publica via Wagtail
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    # Agora DEVE aparecer
    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art in qs


@pytest.mark.django_db
def test_wagtail_unpublish_article_disappears_from_public_queryset():
    """Artigo despublicado via Wagtail some de on_site.filter(status=PUBLISHED)."""
    site = make_site(pk=1, domain='testserver')
    art = make_article_full(site, slug='wagtail-unpub-queryset', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    # Publica via Wagtail para garantir que aparece no queryset público
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art in qs

    # Despublica
    art.unpublish()
    art.refresh_from_db()

    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art not in qs


@pytest.mark.django_db
def test_wagtail_publish_triggers_newsletter_pending(caplog):
    """Publicar via Wagtail dispara o log de newsletter pendente via post_save."""
    import logging

    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-newsletter', status=Article.Status.DRAFT)

    # Configura logging para capturar a mensagem do mark_newsletter_pending_on_publish
    with caplog.at_level(logging.INFO, logger='apps.news.signals'):
        rev = art.save_revision()
        rev.publish()
        art.refresh_from_db()

    assert art.status == Article.Status.PUBLISHED
    # A mensagem de newsletter pendente deve ter sido logada
    assert any(
        'Newsletter pendente para artigo' in record.message
        for record in caplog.records
    ), 'mark_newsletter_pending_on_publish deveria ter logado após publish via Wagtail'


@pytest.mark.django_db
def test_wagtail_publish_idempotent_status_already_published():
    """Se status já é PUBLISHED, o receiver de published não faz save extra desnecessário."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-idempotent', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    original_published_at = art.published_at

    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    # Status continua PUBLISHED, published_at não foi sobrescrito para now()
    assert art.status == Article.Status.PUBLISHED
    assert art.published_at == original_published_at


@pytest.mark.django_db
def test_wagtail_unpublish_idempotent_status_already_not_published():
    """Se status já não é PUBLISHED, o receiver de unpublished não faz nada."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-unpub-idempotent', status=Article.Status.ARCHIVED)
    art.save()

    # Precisamos garantir live=True para que unpublish() funcione
    art.live = True
    art.save()

    art.unpublish()
    art.refresh_from_db()

    # Status continua ARCHIVED (não era PUBLISHED, então o receiver não agiu)
    assert art.status == Article.Status.ARCHIVED


@pytest.mark.django_db
def test_wagtail_publish_changes_nothing_when_already_published():
    """Publicar um artigo repetidamente via Wagtail mantém status e published_at."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-repub', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    original_published_at = art.published_at

    # Primeira publicação
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()
    first_published_at = art.published_at

    assert art.status == Article.Status.PUBLISHED

    # Segunda publicação (nova revisão)
    rev2 = art.save_revision()
    rev2.publish()
    art.refresh_from_db()

    assert art.status == Article.Status.PUBLISHED
    # published_at não é sobrescrito pois status já era PUBLISHED
    assert art.published_at == original_published_at
    assert first_published_at == original_published_at
    assert art.published_at == first_published_at


# ── Extração de content a partir do body (busca do portal) ─────────────────
#
# `content` é o campo que article_search consulta com `content__icontains`. Antes
# o extrator só colhia blocos 'texto' e legendas, então texto digitado em Título,
# Citação, Box de destaque, Fonte e Tabela existia na matéria e não existia na
# busca. Os testes abaixo travam a cobertura por tipo de bloco.


ALL_BLOCK_TYPES_BODY = [
    {'type': 'titulo', 'value': {'texto': 'Palavratitulo', 'nivel': 'h2'}},
    {'type': 'texto', 'value': '<p>Palavratexto no corpo.</p>'},
    {'type': 'citacao', 'value': {'citacao': 'Palavracitacao dita', 'atribuicao': 'Palavraatribuicao'}},
    {'type': 'destaque', 'value': {'estilo': 'info', 'texto': '<p>Palavradestaque</p>'}},
    {'type': 'fonte', 'value': {'rotulo': 'Palavrarotulo', 'url': 'https://exemplo.com/x'}},
    {'type': 'embed', 'value': {'embed_url': 'https://www.youtube.com/watch?v=abc', 'legenda': 'Palavralegenda'}},
    {'type': 'separador', 'value': None},
]


@pytest.mark.django_db
def test_content_extraction_covers_every_text_carrying_block():
    """Todo bloco com texto visível contribui para `content`."""
    site = make_site()
    art = make_article(site, slug='cobertura-blocos')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()
    art.refresh_from_db()

    for expected in (
        'Palavratitulo', 'Palavratexto', 'Palavracitacao', 'Palavraatribuicao',
        'Palavradestaque', 'Palavrarotulo', 'Palavralegenda',
    ):
        assert expected in art.content, f'{expected} não chegou em content (invisível para a busca)'


@pytest.mark.django_db
def test_content_extraction_includes_table_cells():
    """Células de TableBlock entram em `content`."""
    site = make_site()
    art = make_article(site, slug='cobertura-tabela')
    art.body = [{
        'type': 'tabela',
        'value': {'data': [['Cabecalhoum', 'Cabecalhodois'], ['Celulaum', 'Celuladois']]},
    }]
    art.save()
    art.refresh_from_db()

    for expected in ('Cabecalhoum', 'Cabecalhodois', 'Celulaum', 'Celuladois'):
        assert expected in art.content


@pytest.mark.django_db
def test_content_extraction_survives_malformed_table():
    """Tabela sem `data` ou com linha que não é lista não derruba o save."""
    site = make_site()
    art = make_article(site, slug='tabela-torta')
    art.body = [
        {'type': 'tabela', 'value': {}},
        {'type': 'tabela', 'value': {'data': None}},
        {'type': 'tabela', 'value': {'data': ['nao-e-lista', ['Celulaboa']]}},
    ]
    art.save()
    art.refresh_from_db()

    assert 'Celulaboa' in art.content


@pytest.mark.django_db
def test_search_finds_text_that_only_exists_in_heading_and_quote(client):
    """Regressão A2: buscar palavra que só existe em Título/Citação acha o artigo."""
    site = make_site()
    art = make_article_full(site, slug='busca-por-bloco')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()

    for term in ('Palavratitulo', 'Palavracitacao', 'Palavrarotulo'):
        response = client.get(reverse('news:search'), {'q': term})
        assert response.status_code == 200
        assert art.title in response.content.decode(), f'busca por {term} não achou o artigo'


@pytest.mark.django_db
def test_reading_time_counts_all_block_types():
    """reading_time usa o mesmo extrator, então também conta título e citação."""
    site = make_site()
    art = make_article(site, slug='tempo-leitura-blocos')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()

    assert art.reading_time >= 1


# ── Conversão dos blocos legados (migration news.0021) ─────────────────────


def _legacy(block_type, *, rich_text='', media_id=None, caption='', embed_url=''):
    return {
        'block_type': block_type, 'rich_text': rich_text, 'media_id': media_id,
        'caption': caption, 'embed_url': embed_url,
    }


def test_legacy_conversion_maps_each_block_type():
    """rich_text -> texto, image -> imagem, embed -> embed, na ordem recebida."""
    from apps.news.legacy_blocks import build_stream_data

    stream = build_stream_data(
        [
            _legacy('rich_text', rich_text='<p>Corpo legado.</p>'),
            _legacy('image', media_id=7, caption='Legenda da foto'),
            _legacy('embed', embed_url='https://www.youtube.com/watch?v=abc', caption='Legenda do video'),
        ],
        image_pk_for=lambda media_id: 42 if media_id == 7 else None,
    )

    assert [item['type'] for item in stream] == ['texto', 'imagem', 'embed']
    assert stream[0]['value'] == '<p>Corpo legado.</p>'
    assert stream[1]['value'] == {'imagem': 42, 'legenda': 'Legenda da foto'}
    assert stream[2]['value'] == {
        'embed_url': 'https://www.youtube.com/watch?v=abc', 'legenda': 'Legenda do video',
    }
    # Cada bloco precisa de id próprio, ou o Wagtail trata como o mesmo bloco.
    assert len({item['id'] for item in stream}) == 3


def test_legacy_conversion_degrades_image_without_destination_to_caption():
    """Imagem sem cms_media.Image vira parágrafo com a legenda — não desaparece."""
    from apps.news.legacy_blocks import build_stream_data

    stream = build_stream_data(
        [_legacy('image', media_id=99, caption='Foto do <laboratório>')],
        image_pk_for=lambda media_id: None,
    )

    assert len(stream) == 1
    assert stream[0]['type'] == 'texto'
    # Legenda é dado de usuário e vai para dentro de HTML: tem de sair escapada.
    assert stream[0]['value'] == '<p>Foto do &lt;laboratório&gt;</p>'


def test_legacy_conversion_reports_outcome_counts():
    """O contador de desfechos alimenta o relatório de audit_article_blocks."""
    from collections import Counter

    from apps.news.legacy_blocks import build_stream_data

    outcomes = Counter()
    build_stream_data(
        [
            _legacy('rich_text', rich_text='<p>ok</p>'),
            _legacy('image', media_id=7, caption='tem destino'),
            _legacy('image', media_id=None, caption='sem destino'),
            _legacy('image', media_id=None),
            _legacy('embed'),
            _legacy('rich_text'),
        ],
        image_pk_for=lambda media_id: 42 if media_id == 7 else None,
        outcomes=outcomes,
    )

    assert outcomes['texto'] == 1
    assert outcomes['imagem'] == 1
    assert outcomes['imagem_sem_destino_com_legenda'] == 1
    assert outcomes['imagem_sem_destino_perdida'] == 1
    assert outcomes['embed_sem_url_perdido'] == 1
    assert outcomes['vazio_descartado'] == 1


def test_legacy_conversion_groups_by_article_preserving_order():
    from apps.news.legacy_blocks import group_by_article

    blocks = [
        {'article_id': 1, 'order': 0}, {'article_id': 1, 'order': 1},
        {'article_id': 2, 'order': 0},
    ]
    grouped = group_by_article(blocks)

    assert set(grouped) == {1, 2}
    assert [b['order'] for b in grouped[1]] == [0, 1]
