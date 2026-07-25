from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager
from wagtail.documents.models import AbstractDocument
from wagtail.documents.models import Document as WagtailDocument
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.images.models import Image as WagtailImage


class Image(AbstractImage):
    """Imagem personalizada com crédito e ponte para a biblioteca legada."""

    credit = models.CharField(
        'Crédito',
        max_length=255,
        blank=True,
        help_text='Fotógrafo ou fonte da imagem.',
    )
    legacy_media_file_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Referência interna para migração da biblioteca de mídia legada (media_library.MediaFile). Usado apenas durante a migração de dados.',
    )

    # Override inherited fields to avoid reverse-accessor clashes with the
    # stock wagtailimages.Image model, which still exists in the app registry
    # when WAGTAILIMAGES_IMAGE_MODEL is set.
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('uploaded by user'),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name='cms_img_uploaded_by+',
    )
    tags = TaggableManager(
        help_text=None,
        blank=True,
        verbose_name=_('tags'),
        related_name='cms_img_tags+',
    )

    admin_form_fields = WagtailImage.admin_form_fields + (
        'credit',
    )

    @property
    def default_alt_text(self):
        # Force editors to add specific alt text — do not fall back to
        # the title (typically derived from the file name).
        return getattr(self, 'description', None)

    class Meta:
        verbose_name = 'Imagem'
        verbose_name_plural = 'Imagens'
        permissions = [('choose_image', 'Can choose image')]


class Rendition(AbstractRendition):
    """Recortes/redimensionamentos da imagem personalizada."""

    image = models.ForeignKey(
        Image,
        on_delete=models.CASCADE,
        related_name='renditions',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('image', 'filter_spec', 'focal_point_key'),
                name='unique_rendition',
            ),
        ]
        verbose_name = 'Recorte'
        verbose_name_plural = 'Recortes'


class Document(AbstractDocument):
    """Documento personalizado com ponte para a biblioteca legada."""

    legacy_media_file_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Referência interna para migração da biblioteca de mídia legada (media_library.MediaFile). Usado apenas durante a migração de dados.',
    )

    # Override inherited fields to avoid reverse-accessor clashes with the
    # stock wagtaildocs.Document model, which still exists in the app registry
    # when WAGTAILDOCS_DOCUMENT_MODEL is set.
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('uploaded by user'),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name='cms_doc_uploaded_by+',
    )
    tags = TaggableManager(
        help_text=None,
        blank=True,
        verbose_name=_('tags'),
        related_name='cms_doc_tags+',
    )

    admin_form_fields = WagtailDocument.admin_form_fields + (
        # legacy_media_file_id is intentionally excluded — internal migration field.
    )

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        permissions = [('choose_document', 'Can choose document')]
