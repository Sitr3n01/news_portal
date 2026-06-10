"""Validação reutilizável de imagens enviadas por usuários.

Ponto único de validação de upload de imagem do projeto. Usado hoje pelo avatar
do CustomUser e pronto para os demais ImageField (artigos, escola) reaproveitarem
o mesmo padrão — extensão + tamanho + conteúdo real (Pillow), com mensagens
genéricas em PT-BR (convenção de segurança: não revelar detalhe interno).
"""
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image

# ── Padrão de avatar (centralizado e reaproveitável) ─────────────────────────
AVATAR_SIZE = 256          # lado do quadrado final, em pixels
AVATAR_JPEG_QUALITY = 82   # qualidade do JPEG de saída (equilíbrio nitidez × peso)

# ── Padrão de imagem de capa de artigo ───────────────────────────────────────
# Capa preserva proporção (ResizeToFit), só limita o lado maior — diferente do
# avatar, que recorta em quadrado (ResizeToFill). Mesmo validador, mesma higiene.
ARTICLE_IMAGE_MAX_WIDTH = 1600    # limite do lado maior, em pixels
ARTICLE_IMAGE_MAX_HEIGHT = 1600
ARTICLE_IMAGE_JPEG_QUALITY = 82

# Teto do arquivo recebido, ANTES do processamento. Fica abaixo do
# client_max_body_size 10M do nginx para dar erro amigável antes do 413.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# Mensagem única e genérica para qualquer falha de validação.
_GENERIC_ERROR = 'Envie uma imagem válida (JPG, PNG ou WebP) de até 5 MB.'


def validate_uploaded_image(image):
    """Valida extensão, tamanho e conteúdo real de uma imagem enviada.

    - extensão na lista branca (ALLOWED_IMAGE_EXTENSIONS);
    - tamanho ≤ MAX_UPLOAD_BYTES;
    - conteúdo decodificável pelo Pillow — rejeita arquivo renomeado/corrompido
      ou HEIC sem suporte, equivalendo a uma checagem de tipo real sem depender
      de python-magic.

    Rebobina o ponteiro do arquivo ao final para que o processamento posterior
    (imagekit no save) consiga relê-lo.
    """
    name = getattr(image, 'name', '') or ''
    if Path(name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(_GENERIC_ERROR)

    size = getattr(image, 'size', None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise ValidationError(_GENERIC_ERROR)

    try:
        image.seek(0)
        Image.open(image).verify()
    except Exception as exc:
        raise ValidationError(_GENERIC_ERROR) from exc
    finally:
        try:
            image.seek(0)
        except Exception:
            pass
