"""Formatos de data do projeto em pt-BR (FORMAT_MODULE_PATH).

Só o que muda em relação ao pt-BR do Django: data e hora curtas nas telas do
painel ("24/07/2026 18:27", como nas listas do Wagtail), no lugar de "24 de
Julho de 2026 às 18:27", que quebrava em duas linhas nas colunas das listas do
Django admin. O resto (entrada de datas, meses por extenso quando pedidos com
formato explícito) segue o do Django. O site público sempre passa o formato
explícito (`|date:"..."`), então não muda.
"""

DATE_FORMAT = 'd/m/Y'
DATETIME_FORMAT = 'd/m/Y H:i'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
