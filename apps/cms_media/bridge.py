"""Criação de ``cms_media.Image`` a partir das fontes de imagem legadas.

Duas pontes de migração fazem a mesma mecânica de "bytes na mão → Image do
Wagtail": a capa do artigo (``Article.featured_image``, comando
``migrate_featured_images``) e as imagens dos blocos de conteúdo
(``media_library.MediaFile``, comando ``migrate_block_media``). Leitura de
arquivo, extração de dimensões e criação do registro moram aqui para que as duas
não divirjam.

Regra que justifica a separação entre ler e criar: ``ContentFile`` **grava o
arquivo no MEDIA_ROOT**, e isso não é desfeito por rollback de transação. Um
dry-run honesto precisa poder validar a fonte sem materializar destino, então
``read_source_bytes``/``image_dimensions`` são inofensivos e só
``create_wagtail_image`` escreve.
"""

import os
from io import BytesIO

from django.core.files.base import ContentFile


def read_source_bytes(file_field):
    """Lê o conteúdo de um ``FileField``/``ImageField`` legado.

    Devolve ``(conteudo, nome_do_arquivo, erro)`` — ``erro`` é ``None`` no
    sucesso. Nunca levanta: arquivo referenciado no banco mas ausente do disco é
    o caso comum em acervo herdado, e o chamador precisa contabilizar em vez de
    abortar a migração inteira.
    """
    try:
        file_field.open('rb')
        content = file_field.read()
    except Exception as exc:
        return None, '', str(exc)
    finally:
        try:
            file_field.close()
        except Exception:
            pass

    if not content:
        return None, '', 'arquivo vazio (0 bytes)'

    return content, os.path.basename(file_field.name), None


def image_dimensions(content):
    """``(largura, altura)`` via Pillow; ``(0, 0)`` se não for imagem legível."""
    from PIL import Image as PILImage

    try:
        with PILImage.open(BytesIO(content)) as pil_image:
            return pil_image.size
    except Exception:
        return 0, 0


def create_wagtail_image(*, content, filename, title, description='', legacy_media_file_id=None):
    """Cria uma ``cms_media.Image`` a partir de bytes, gravando o arquivo.

    Só chame quando for para persistir de verdade — ver a observação sobre
    ``ContentFile`` no docstring do módulo.

    ``description`` alimenta ``Image.default_alt_text``, então é por aqui que o
    ``alt_text`` da biblioteca legada sobrevive à migração.
    """
    from wagtail.images import get_image_model

    width, height = image_dimensions(content)
    return get_image_model().objects.create(
        title=(title or filename or 'Imagem')[:255],
        description=(description or '')[:255],
        width=width,
        height=height,
        file=ContentFile(content, name=filename),
        file_size=len(content),
        legacy_media_file_id=legacy_media_file_id,
    )
