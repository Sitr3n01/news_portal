from django import template

from apps.school.courses import title_for_display

register = template.Library()


@register.filter
def soft_hyphens(title):
    """Título de curso com hífen condicional nas palavras compridas (ver apps.school.courses.title_for_display).

    Para o H1 da página do curso e os cards de Cursos. Em x-text, use antes do escapejs:
    {{ course.title_en|soft_hyphens|escapejs }}.
    """
    return title_for_display(str(title))
