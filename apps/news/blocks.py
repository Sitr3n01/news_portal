"""StreamField block library — MVP Fase 4.

Define os blocos editoriais que compõem o corpo do artigo via StreamField.
Cada bloco é independente e reutilizável; a composição final está em
ArticleStreamBlock, agrupada por categoria (Texto / Mídia / Destaques / Dados).

A biblioteca de blocos é puramente aditiva — ArticleBlock e o sistema de
renderização do site público permanecem intactos.
"""

from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

# ── Features do RichTextBlock derivadas do allowlist de sanitização ──────────
# apps/common/sanitization.py define ALLOWED_TAGS como o conjunto seguro de
# tags HTML. Derivamos um subconjunto apropriado para o editor rich text,
# excluindo headings (têm bloco dedicado), imagens (têm bloco dedicado),
# tabelas (têm bloco dedicado) e iframe (não é conteúdo editorial direto).
#
# Títulos h2-h4 são tratados pelo HeadingBlock — removemos do rich text
# para evitar dois caminhos de criação de headings.
RICH_TEXT_FEATURES = [
    'bold', 'italic', 'underline', 'strikethrough',
    'ol', 'ul',
    'link', 'document-link',
    'blockquote',
    'code', 'superscript', 'subscript',
    'hr',
]

# Para blocos internos (ex.: CalloutBlock) o rich text é mais restrito ainda.
MINIMAL_RICH_TEXT_FEATURES = ['bold', 'italic', 'link']


# ── Blocos individuais ───────────────────────────────────────────────────────


class HeadingBlock(blocks.StructBlock):
    """Título ou subtítulo — h2, h3 ou h4."""

    texto = blocks.CharBlock(label='Texto', required=True)
    nivel = blocks.ChoiceBlock(
        choices=[
            ('h2', 'Título'),
            ('h3', 'Subtítulo'),
            ('h4', 'Subtítulo menor'),
        ],
        default='h2',
        label='Nível',
    )

    class Meta:
        icon = 'title'
        label = 'Título / Subtítulo'
        template = 'news/blocks/heading.html'


class ImageBlock(blocks.StructBlock):
    """Imagem inline com legenda opcional.

    Crédito fica no modelo customizado de Imagem (cms_media.Image.credit) —
    não duplicamos aqui.
    """

    imagem = ImageChooserBlock(required=True, label='Imagem')
    legenda = blocks.CharBlock(required=False, label='Legenda')

    class Meta:
        icon = 'image'
        label = 'Imagem'
        template = 'news/blocks/image.html'


class EmbedBlock(blocks.StructBlock):
    """Embed de vídeo/post (YouTube, Instagram, TikTok).

    Diferente do wagtail.embeds.blocks.EmbedBlock (que usa oEmbed), este bloco
    resolve a URL via apps.common.embeds.resolve_embed(), espelhando o
    funcionamento atual de ArticleBlock.embed.
    """

    embed_url = blocks.URLBlock(
        label='Link do vídeo/post',
        help_text='Cole o link do YouTube, Instagram ou TikTok.',
        required=True,
    )
    legenda = blocks.CharBlock(
        required=False,
        label='Legenda',
        help_text='Texto opcional exibido abaixo do vídeo/post.',
    )

    class Meta:
        icon = 'media'
        label = 'Vídeo / Post'
        template = 'news/blocks/embed.html'

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        from apps.common.embeds import resolve_embed
        context['embed_data'] = resolve_embed(value.get('embed_url', ''))
        return context


class QuoteBlock(blocks.StructBlock):
    """Citação com atribuição opcional."""

    citacao = blocks.TextBlock(label='Citação', required=True)
    atribuicao = blocks.CharBlock(required=False, label='Atribuição')

    class Meta:
        icon = 'openquote'
        label = 'Citação'
        template = 'news/blocks/quote.html'


class SeparatorBlock(blocks.StaticBlock):
    """Linha separadora horizontal."""

    class Meta:
        icon = 'horizontalrule'
        label = 'Separador'
        admin_text = 'Linha separadora'
        template = 'news/blocks/separator.html'


class CalloutBlock(blocks.StructBlock):
    """Box de destaque editorial (informativo, alerta ou destaque)."""

    estilo = blocks.ChoiceBlock(
        choices=[
            ('info', 'Informativo'),
            ('alerta', 'Alerta'),
            ('destaque', 'Destaque'),
        ],
        default='info',
        label='Estilo',
    )
    texto = blocks.RichTextBlock(
        features=MINIMAL_RICH_TEXT_FEATURES,
        label='Texto',
    )

    class Meta:
        icon = 'help'
        label = 'Box de destaque'
        template = 'news/blocks/callout.html'


class SourceBlock(blocks.StructBlock):
    """Fonte ou referência com link."""

    rotulo = blocks.CharBlock(label='Rótulo', required=True)
    url = blocks.URLBlock(label='Link', required=True)

    class Meta:
        icon = 'link'
        label = 'Fonte / Referência'
        template = 'news/blocks/source.html'


# ── Composição: StreamBlock raiz ─────────────────────────────────────────────


class ArticleStreamBlock(blocks.StreamBlock):
    """Blocos disponíveis para o corpo do artigo, agrupados por categoria.

    Grupos (plano §9):
    - Texto:   título, texto rico, citação, separador
    - Mídia:   imagem, embed, documento
    - Destaques: box de destaque
    - Dados:   tabela, fonte/referência
    """

    titulo = HeadingBlock(group='Texto')
    texto = blocks.RichTextBlock(
        features=RICH_TEXT_FEATURES,
        label='Texto rico',
        icon='pilcrow',
        group='Texto',
    )
    citacao = QuoteBlock(group='Texto')
    separador = SeparatorBlock(group='Texto')

    imagem = ImageBlock(group='Mídia')
    embed = EmbedBlock(group='Mídia')
    documento = DocumentChooserBlock(group='Mídia')

    destaque = CalloutBlock(group='Destaques')

    tabela = TableBlock(group='Dados')
    fonte = SourceBlock(group='Dados')

    class Meta:
        label = 'Blocos de conteúdo'
        group = {'Texto': ['titulo', 'texto', 'citacao', 'separador'],
                 'Mídia': ['imagem', 'embed', 'documento'],
                 'Destaques': ['destaque'],
                 'Dados': ['tabela', 'fonte']}
