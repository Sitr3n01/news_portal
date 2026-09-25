"""Gera o relatório de auditoria de segurança em PDF (A4, pt-BR).

Uso, em ambiente isolado (nada é instalado globalmente):

    python3 -m venv .venv-relatorio
    .venv-relatorio/bin/pip install -r docs/security-audit/requirements.txt
    .venv-relatorio/bin/python docs/security-audit/gerar_relatorio.py
    # opcional: rasterizar as páginas para conferência visual
    .venv-relatorio/bin/python docs/security-audit/gerar_relatorio.py --previa /tmp/previa-relatorio

Saída: docs/security-audit/relatorio-auditoria-seguranca.pdf. O conteúdo vem de
dados_auditoria.py (mesma pasta); este arquivo só cuida do desenho.
"""

import argparse
import math
import re
import tempfile
import textwrap
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import dados_auditoria as dados
import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / 'relatorio-auditoria-seguranca.pdf'

LARGURA, ALTURA = A4
ALTURA_FAIXA = 8.1 * cm
MARGEM = 2 * cm
UTIL = LARGURA - 2 * MARGEM

# Tokens de cor. Texto sempre em tinta neutra; a cor da severidade fica no chip/marca.
TINTA = '#0F172A'
TEXTO = '#1F2937'
SUAVE = '#6B7280'
LINHA = '#E5E7EB'
FUNDO = '#F8FAFC'
CODIGO = '#F1F5F9'
FAIXA = '#0F172A'
PALETA = dados.PALETA
ROTULO_SEV = dict(dados.SEVERIDADES)
# Branco sobre o âmbar da "média" fica abaixo de 3:1 — ali o texto do chip é escuro.
TEXTO_CHIP = {'media': TINTA}

# ── Fontes (DejaVu vem junto com o matplotlib: sem depender do sistema) ──────
_TTF = Path(matplotlib.get_data_path()) / 'fonts' / 'ttf'
for _nome, _arquivo in (
    ('Sans', 'DejaVuSans.ttf'),
    ('Sans-Bold', 'DejaVuSans-Bold.ttf'),
    ('Sans-Oblique', 'DejaVuSans-Oblique.ttf'),
    ('Sans-BoldOblique', 'DejaVuSans-BoldOblique.ttf'),
    ('Mono', 'DejaVuSansMono.ttf'),
    ('Mono-Bold', 'DejaVuSansMono-Bold.ttf'),
):
    pdfmetrics.registerFont(TTFont(_nome, str(_TTF / _arquivo)))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-Bold', italic='Sans-Oblique', boldItalic='Sans-BoldOblique')
pdfmetrics.registerFontFamily('Mono', normal='Mono', bold='Mono-Bold', italic='Mono', boldItalic='Mono-Bold')


def _estilo(nome, **kw):
    base = {'fontName': 'Sans', 'fontSize': 9, 'leading': 13, 'textColor': colors.HexColor(TEXTO), 'alignment': TA_LEFT}
    base.update(kw)
    return ParagraphStyle(nome, **base)


E = {
    'corpo': _estilo('corpo', spaceAfter=6),
    'pequeno': _estilo('pequeno', fontSize=7.8, leading=10.6),
    'suave': _estilo('suave', fontSize=7.8, leading=10.6, textColor=colors.HexColor(SUAVE), spaceAfter=6),
    'capa_celula': _estilo('capa_celula', fontSize=7.2, leading=9.6),
    'celula': _estilo('celula', fontSize=7.6, leading=10.2),
    'celula_b': _estilo('celula_b', fontName='Sans-Bold', fontSize=7.6, leading=10.2, textColor=colors.HexColor(TINTA)),
    'celula_mono': _estilo('celula_mono', fontName='Mono', fontSize=6.5, leading=9, textColor=colors.HexColor(TINTA)),
    'th': _estilo('th', fontName='Sans-Bold', fontSize=7.6, leading=10, textColor=colors.white),
    'h1': _estilo('h1', fontName='Sans-Bold', fontSize=16, leading=20, textColor=colors.HexColor(TINTA), spaceBefore=4, spaceAfter=10),
    'h2': _estilo('h2', fontName='Sans-Bold', fontSize=11.5, leading=15, textColor=colors.HexColor(TINTA), spaceBefore=10, spaceAfter=6),
    'h3': _estilo('h3', fontName='Sans-Bold', fontSize=9.5, leading=13, textColor=colors.HexColor(TINTA), spaceBefore=4, spaceAfter=3),
    'codigo': _estilo('codigo', fontName='Mono', fontSize=7, leading=9.2, textColor=colors.HexColor(TINTA),
                      backColor=colors.HexColor(CODIGO), borderPadding=(5, 6, 5, 6), leftIndent=6, rightIndent=6,
                      spaceBefore=5, spaceAfter=9),
    'issue': _estilo('issue', fontName='Mono', fontSize=7.1, leading=9.3, textColor=colors.HexColor(TINTA),
                     backColor=colors.HexColor(CODIGO), borderPadding=(6, 6, 6, 6), leftIndent=6, rightIndent=6,
                     spaceBefore=4, spaceAfter=4),
    'delim': _estilo('delim', fontName='Mono-Bold', fontSize=7.6, leading=10, textColor=colors.HexColor(SUAVE)),
    'kpi_n': _estilo('kpi_n', fontName='Sans-Bold', fontSize=17, leading=20, textColor=colors.HexColor(TINTA)),
    'kpi_l': _estilo('kpi_l', fontSize=7, leading=9, textColor=colors.HexColor(SUAVE)),
}


def p(texto, estilo='corpo'):
    return Paragraph(texto, E[estilo])


# ── Peças de desenho ─────────────────────────────────────────────────────────


class Chip(Flowable):
    """Selo de severidade: sempre com o rótulo escrito, nunca só a cor."""

    def __init__(self, texto, cor, cor_texto='#FFFFFF', tamanho=6.6):
        super().__init__()
        self.texto = texto.upper()
        self.cor = cor
        self.cor_texto = cor_texto
        self.tamanho = tamanho
        self.largura = stringWidth(self.texto, 'Sans-Bold', tamanho) + 11
        self.altura = tamanho + 6.5

    def wrap(self, disponivel_l, disponivel_a):
        return self.largura, self.altura

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor(self.cor))
        c.roundRect(0, 0, self.largura, self.altura, self.altura / 2, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(self.cor_texto))
        c.setFont('Sans-Bold', self.tamanho)
        c.drawCentredString(self.largura / 2, (self.altura - self.tamanho) / 2 + 1.1, self.texto)


def chip_sev(sev, tamanho=6.2):
    return Chip(ROTULO_SEV[sev], PALETA[sev], TEXTO_CHIP.get(sev, '#FFFFFF'), tamanho=tamanho)


def tabela(linhas, larguras, cabecalho=True, zebra=True, extra=None):
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    estilo = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor(LINHA)),
    ]
    if cabecalho:
        estilo += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(TINTA)), ('VALIGN', (0, 0), (-1, 0), 'MIDDLE')]
    if zebra:
        inicio = 1 if cabecalho else 0
        for i in range(inicio, len(linhas)):
            if (i - inicio) % 2 == 1:
                estilo.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor(FUNDO)))
    t.setStyle(TableStyle(estilo + (extra or [])))
    return t


def bloco_codigo(texto, estilo='codigo'):
    return XPreformatted(escape(texto), E[estilo])


def imagem(caminho, largura):
    w, h = ImageReader(str(caminho)).getSize()
    return Image(str(caminho), width=largura, height=largura * h / w)


class CanvasNumerado(canvas.Canvas):
    """Cabeçalho e rodapé com "Página X de Y" (precisa do total, por isso a 2ª passada)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):  # noqa: N802 — nome da API do reportlab
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._moldura(total)
            super().showPage()
        super().save()

    def _moldura(self, total):
        if self._pageNumber == 1:
            return
        self.saveState()
        self.setStrokeColor(colors.HexColor(LINHA))
        self.setLineWidth(0.6)
        topo = ALTURA - 1.35 * cm
        self.line(MARGEM, topo - 0.18 * cm, LARGURA - MARGEM, topo - 0.18 * cm)
        self.line(MARGEM, 1.5 * cm, LARGURA - MARGEM, 1.5 * cm)
        self.setFillColor(colors.HexColor(SUAVE))
        self.setFont('Sans-Bold', 7.4)
        self.drawString(MARGEM, topo, dados.TITULO)
        self.setFont('Sans', 7.4)
        self.drawRightString(LARGURA - MARGEM, topo, 'Uso interno — contém detalhes de vulnerabilidades')
        self.drawString(MARGEM, 1.05 * cm, f'{dados.TITULO} · {dados.DATA}')
        self.drawRightString(LARGURA - MARGEM, 1.05 * cm, f'Página {self._pageNumber} de {total}')
        self.restoreState()


# ── Números ──────────────────────────────────────────────────────────────────


def contagens():
    por_sev = Counter(a['sev'] for a in dados.ACHADOS)
    por_cat = {c['id']: Counter(a['sev'] for a in dados.ACHADOS if a['cat'] == c['id']) for c in dados.CATEGORIAS}
    fortes = Counter(cat for cat, *_ in dados.PONTOS_FORTES)
    return por_sev, por_cat, fortes


# ── Gráficos (matplotlib sem pyplot) ─────────────────────────────────────────

ORDEM_SEV = [k for k, _ in dados.SEVERIDADES]
SEV_POR_ID = {a['id']: a['sev'] for a in dados.ACHADOS}


def _cor_rotulo(sev):
    return TINTA if sev == 'media' else '#FFFFFF'


def grafico_rosca(por_sev, destino):
    fig = Figure(figsize=(6.4 / 2.54, 7.3 / 2.54), dpi=300)
    ax = fig.add_axes([0.03, 0.24, 0.94, 0.74])
    itens = [(k, por_sev[k]) for k in ORDEM_SEV if por_sev[k]]
    fatias, _ = ax.pie(
        [n for _, n in itens], colors=[PALETA[k] for k, _ in itens], startangle=90, counterclock=False,
        wedgeprops={'width': 0.36, 'edgecolor': 'white', 'linewidth': 2.4},
    )
    for fatia, (sev, n) in zip(fatias, itens):
        if sev == 'media':
            fatia.set_hatch('////')  # 2ª codificação: alta e média são próximas na paleta
        angulo = math.radians((fatia.theta1 + fatia.theta2) / 2)
        ax.text(0.82 * math.cos(angulo), 0.82 * math.sin(angulo), str(n), ha='center', va='center',
                fontsize=9, fontweight='bold', color=_cor_rotulo(sev),
                bbox={'boxstyle': 'circle,pad=0.18', 'fc': PALETA[sev], 'ec': 'none'} if sev == 'media' else None)
    total = sum(por_sev.values())
    ax.text(0, 0.1, str(total), ha='center', va='center', fontsize=21, fontweight='bold', color=TINTA)
    ax.text(0, -0.24, 'achados', ha='center', va='center', fontsize=7.5, color=SUAVE)
    ax.set_aspect('equal')
    alcas = [Patch(facecolor=PALETA[k], edgecolor='white', hatch='////' if k == 'media' else None) for k in ORDEM_SEV]
    rotulos = [f'{ROTULO_SEV[k]} — {por_sev[k]}' for k in ORDEM_SEV]
    fig.legend(alcas, rotulos, loc='lower center', ncol=2, frameon=False, fontsize=7, labelcolor=TEXTO,
               handlelength=1.2, handleheight=1.0, columnspacing=1.2, bbox_to_anchor=(0.5, 0.0))
    fig.savefig(destino, facecolor='white')


def grafico_barras(por_cat, fortes, destino):
    fig = Figure(figsize=(6.9, 3.05), dpi=240)
    grade = fig.add_gridspec(1, 2, width_ratios=[1.6, 1], wspace=0.06, left=0.25, right=0.985, top=0.86, bottom=0.25)
    ax = fig.add_subplot(grade[0])
    ax2 = fig.add_subplot(grade[1], sharey=ax)
    cats = dados.CATEGORIAS
    ys = list(range(len(cats)))[::-1]
    esquerda = [0] * len(cats)
    for sev in ORDEM_SEV:
        valores = [por_cat[c['id']][sev] for c in cats]
        if not any(valores):
            continue
        ax.barh(ys, valores, left=esquerda, height=0.58, color=PALETA[sev], edgecolor='white', linewidth=1.6,
                hatch='////' if sev == 'media' else None, label=ROTULO_SEV[sev])
        for y, v, x0 in zip(ys, valores, esquerda):
            if v:
                ax.text(x0 + v / 2, y, str(v), ha='center', va='center', fontsize=7.4, fontweight='bold',
                        color=_cor_rotulo(sev),
                        bbox={'boxstyle': 'circle,pad=0.15', 'fc': PALETA[sev], 'ec': 'none'} if sev == 'media' else None)
        esquerda = [a + b for a, b in zip(esquerda, valores)]
    for y, total in zip(ys, esquerda):
        ax.text(total + 0.08, y, f'{total}', ha='left', va='center', fontsize=7.6, color=TINTA, fontweight='bold')
    ax.set_yticks(ys, [c['curto'] for c in cats], fontsize=7.8, color=TINTA)
    ax.set_xlim(0, max(esquerda) + 0.8)
    ax.set_xticks(range(0, max(esquerda) + 1))
    ax.set_title('Achados por categoria e severidade', fontsize=8.6, color=TINTA, loc='left', fontweight='bold')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=4, frameon=False, fontsize=7.2, labelcolor=TEXTO,
              handlelength=1.1, columnspacing=1.0)

    valores = [fortes[c['id']] for c in cats]
    ax2.barh(ys, valores, height=0.58, color=PALETA['forte'], edgecolor='white', linewidth=1.6)
    for y, v in zip(ys, valores):
        ax2.text(v + 0.15, y, str(v), ha='left', va='center', fontsize=7.6, color=TINTA, fontweight='bold')
    ax2.set_xlim(0, max(valores) + 1.6)
    ax2.set_title('Pontos fortes verificados', fontsize=8.6, color=TINTA, loc='left', fontweight='bold')
    ax2.tick_params(axis='y', left=False, labelleft=False)

    for eixo in (ax, ax2):
        for lado in ('top', 'right', 'left'):
            eixo.spines[lado].set_visible(False)
        eixo.spines['bottom'].set_color(LINHA)
        eixo.tick_params(axis='x', colors=SUAVE, labelsize=7, length=0)
        eixo.tick_params(axis='y', length=0)
        eixo.grid(axis='x', color=LINHA, linewidth=0.6)
        eixo.set_axisbelow(True)
    fig.savefig(destino, facecolor='white')


# ── Seções ───────────────────────────────────────────────────────────────────


def desenhar_capa(c, _doc):
    c.saveState()
    altura_faixa = ALTURA_FAIXA
    c.setFillColor(colors.HexColor(FAIXA))
    c.rect(0, ALTURA - altura_faixa, LARGURA, altura_faixa, stroke=0, fill=1)
    c.setFillColor(colors.HexColor('#93C5FD'))
    c.setFont('Sans-Bold', 8)
    c.drawString(MARGEM, ALTURA - 1.9 * cm, 'AUDITORIA DE SEGURANÇA · 5 CATEGORIAS · PT-BR')
    titulo = Paragraph(escape(dados.TITULO), _estilo('capa_t', fontName='Sans-Bold', fontSize=22, leading=26.5, textColor=colors.white))
    _, h = titulo.wrap(UTIL, 8 * cm)
    titulo.drawOn(c, MARGEM, ALTURA - 2.25 * cm - h)
    sub = Paragraph('Komuniki (komuniki.com.br) e Blog da Kelly (kellyfarias.com.br/news) — Django + Wagtail',
                    _estilo('capa_s', fontSize=10.5, leading=14, textColor=colors.HexColor('#CBD5E1')))
    _, hs = sub.wrap(UTIL, 3 * cm)
    sub.drawOn(c, MARGEM, ALTURA - 2.5 * cm - h - hs)
    c.setFont('Sans', 8.6)
    c.setFillColor(colors.HexColor('#E2E8F0'))
    c.drawString(MARGEM, ALTURA - altura_faixa + 1.75 * cm, f'Data: {dados.DATA}    ·    Commit auditado: {dados.COMMIT}')
    por_sev, _, fortes = contagens()
    x = MARGEM
    for sev in ORDEM_SEV:
        chip = Chip(f'{por_sev[sev]} {ROTULO_SEV[sev]}', PALETA[sev], TEXTO_CHIP.get(sev, '#FFFFFF'), tamanho=7.4)
        chip.wrap(0, 0)
        chip.drawOn(c, x, ALTURA - altura_faixa + 0.7 * cm)
        x += chip.largura + 6
    chip = Chip(f'{sum(fortes.values())} pontos fortes', PALETA['forte'], tamanho=7.4)
    chip.wrap(0, 0)
    chip.drawOn(c, x, ALTURA - altura_faixa + 0.7 * cm)
    c.restoreState()


def secao_capa():
    s = [Spacer(1, ALTURA_FAIXA - MARGEM + 0.1 * cm), p('Escopo auditado', 'h2')]
    linhas = [[p(f'<b>{escape(k)}</b>', 'capa_celula'), p(escape(v), 'capa_celula')] for k, v in dados.ESCOPO]
    s.append(tabela(linhas, [3.3 * cm, UTIL - 3.3 * cm], cabecalho=False))
    s.append(p('Nota metodológica — como cada categoria foi mapeada para a stack', 'h2'))
    cab = [p('Categoria', 'th'), p('Equivalente na stack detectada', 'th'), p('Como foi verificado', 'th')]
    linhas = [cab] + [
        [p(f'<b>{escape(c["curto"])}</b>', 'capa_celula'), p(escape(c['stack']), 'capa_celula'), p(escape(c['como']), 'capa_celula')]
        for c in dados.CATEGORIAS
    ]
    s.append(tabela(linhas, [2.9 * cm, 7.9 * cm, UTIL - 10.8 * cm]))
    return s


def nota_escala():
    return p('<b>Escala de severidade.</b> <b>Crítica</b>: exploração remota sem autenticação com comprometimento amplo. '
               '<b>Alta</b>: escalada de privilégio ou vazamento relevante com barreira baixa. <b>Média</b>: exige papel '
               'interno ou uma configuração específica. <b>Baixa</b>: condição improvável ou só defesa em profundidade. '
               '<b>Informativa</b>: sem exploração hoje; higiene. Só entram achados verificados no código real: '
               'cada um traz arquivo:linha, trecho e como foi confirmado.', 'suave')


def secao_resumo(por_sev, fortes, graficos):
    s = [PageBreak(), p('1. Resumo executivo', 'h1')]
    total = sum(por_sev.values())
    tiles = [('Achados', total, TINTA)] + [(ROTULO_SEV[k], por_sev[k], PALETA[k]) for k in ORDEM_SEV]
    tiles.append(('Pontos fortes', sum(fortes.values()), PALETA['forte']))
    largura = UTIL / len(tiles)
    linha = [[p(str(n), 'kpi_n'), p(escape(rotulo), 'kpi_l')] for rotulo, n, _ in tiles]
    extra = [('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(FUNDO)),
             ('LINEBEFORE', (1, 0), (-1, 0), 2, colors.white)]
    for i, (_, _, cor) in enumerate(tiles):
        extra.append(('LINEABOVE', (i, 0), (i, 0), 3, colors.HexColor(cor)))
    s.append(tabela([linha], [largura] * len(tiles), cabecalho=False, zebra=False, extra=extra))
    s.append(Spacer(1, 10))
    s.append(p(
        f'Foram percorridos todos os handlers de rota do projeto (inventário na seção 2.3), a configuração de deploy e os 182 '
        f'commits do histórico. Resultado: <b>{total} achados verificados</b> — nenhum crítico, {por_sev["alta"]} altos, '
        f'{por_sev["media"]} médios, {por_sev["baixa"]} baixos e {por_sev["informativa"]} informativos — e '
        f'<b>{sum(fortes.values())} controles confirmados como corretos</b>. Os três achados altos têm a mesma raiz: uma regra '
        'que a interface respeita, mas que o servidor não aplica em todos os caminhos — o limite de superusuário (PRIV-01), o '
        'filtro de publicação nas rotas por ID (IDOR-01) e o tipo de arquivo aceito em uploads servidos na mesma origem dos '
        'painéis (XSS-01). Encadeados, XSS-01 e PRIV-01 levam uma conta de conteúdo até superusuário mesmo quando quem abre o '
        'link é só um Administrador Geral. Todos os achados com exploração foram confirmados em teste dinâmico.'))
    leitura = [
        p('Leitura rápida', 'h3'),
        p('• Nenhum achado crítico; os 3 altos tiveram a exploração confirmada em teste.', 'pequeno'),
        p('• Nenhum segredo real no código, no bundle ou nos 182 commits: o risco de chaves é de processo (SEC-01).', 'pequeno'),
        p('• Sanitização de HTML, autoescape e JS próprio sem sinks: não há XSS por texto; o vetor é upload (XSS-01).', 'pequeno'),
        p('• As correções P1 são pequenas e locais: admin de usuários, duas views e allowlist + nginx.', 'pequeno'),
        Spacer(1, 4),
        p('Paleta fixa do relatório: alta e média são tons próximos; por isso os valores vêm escritos em cada marca '
          'e a média leva hachura.', 'suave'),
    ]
    s.append(Table([[imagem(graficos['rosca'], 6.4 * cm), leitura]], colWidths=[7.0 * cm, UTIL - 7.0 * cm],
                   style=[('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    s.append(Spacer(1, 8))
    s.append(imagem(graficos['barras'], UTIL))
    s.append(Spacer(1, 6))
    s.append(nota_escala())
    return s


def secao_fortes_fracos():
    s = [PageBreak(), p('2. Pontos fortes e pontos fracos', 'h1'), p('2.1 Pontos fortes — o que está protegido', 'h2'),
         p('Cada item foi conferido no código do commit auditado; a evidência aponta onde a proteção mora.', 'suave')]
    nomes = {c['id']: c['curto'] for c in dados.CATEGORIAS}
    cab = [p('Categoria', 'th'), p('Proteção verificada', 'th'), p('Evidência (arquivo:linha)', 'th')]
    linhas = [cab] + [
        [p(escape(nomes[cat]), 'celula_b'), p(escape(txt), 'celula'), p(escape(ev), 'celula_mono')]
        for cat, txt, ev in dados.PONTOS_FORTES
    ]
    s.append(tabela(linhas, [3.0 * cm, 6.6 * cm, UTIL - 9.6 * cm],
                    extra=[('LINEBEFORE', (0, 1), (0, -1), 2.5, colors.HexColor(PALETA['forte']))]))

    s.append(CondPageBreak(6 * cm))
    s.append(p('2.2 Pontos fracos — riscos centrais', 'h2'))
    linhas = [[chip_sev(sev), p(escape(txt), 'celula')] for sev, txt in dados.PONTOS_FRACOS]
    s.append(tabela(linhas, [2.2 * cm, UTIL - 2.2 * cm], cabecalho=False, zebra=True))

    s.append(CondPageBreak(8 * cm))
    s.append(p('2.3 Cobertura da auditoria — inventário de handlers', 'h2'))
    s.append(p('Todas as rotas de config/urls.py e dos apps, mais o admin do Django, o Wagtail e os blocos do nginx. '
               '"OK" significa verificado sem falha nas cinco categorias.', 'suave'))
    cab = [p('Área', 'th'), p('Rotas / handlers', 'th'), p('Resultado', 'th')]
    linhas = [cab]
    for area, rota, res, ids in dados.ROTAS:
        if res == 'OK':
            selo = Chip('OK', PALETA['forte'], tamanho=6.2)
        else:
            sev = min((SEV_POR_ID[i.strip()] for i in ids.split(',')), key=ORDEM_SEV.index)
            selo = Chip(ids, PALETA[sev], TEXTO_CHIP.get(sev, '#FFFFFF'), tamanho=6.2)
        linhas.append([p(escape(area), 'celula_b'), p(escape(rota), 'celula_mono'), selo])
    s.append(tabela(linhas, [3.2 * cm, 10.3 * cm, UTIL - 13.5 * cm]))
    return s


def _locais_celula(achado):
    partes = []
    for local, _ in achado['local']:
        partes += [escape(x.strip()) for x in local.split('·')]
    return p('<br/>'.join(partes), 'celula_mono')


def _cartao(achado):
    cabecalho = Table(
        [[p(f'<b>{achado["id"]}</b>', 'celula_b'), chip_sev(achado['sev']), p(f'<b>{escape(achado["titulo"])}</b>', 'celula')]],
        colWidths=[1.7 * cm, 2.6 * cm, UTIL - 4.3 * cm],
        style=[('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
               ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor(PALETA[achado['sev']]))],
    )
    corpo = [cabecalho, Spacer(1, 4)]
    for rotulo, chave in (('Onde', None), ('Por que é explorável', 'exploravel'), ('Condição de explorabilidade', 'condicao'),
                          ('Como foi verificado', 'verificacao')):
        if chave is None:
            itens = '; '.join(f'<font name="Mono" size="7">{escape(loc)}</font> — {escape(o)}' for loc, o in achado['local'])
            corpo.append(p(f'<b>{rotulo}:</b> {itens}', 'pequeno'))
        else:
            corpo.append(p(f'<b>{rotulo}:</b> {escape(achado[chave])}', 'pequeno'))
    corpo.append(bloco_codigo(achado['trecho']))
    return KeepTogether(corpo)


def secao_achados():
    s = [PageBreak(), p('3. Achados detalhados por categoria', 'h1'),
         p('Cada categoria traz o mecanismo equivalente na stack, a tabela de achados e, em seguida, o detalhe de cada um '
           '(trecho real do código, exploração, condição e forma de verificação).', 'suave')]
    for i, cat in enumerate(dados.CATEGORIAS, start=1):
        achados = sorted((a for a in dados.ACHADOS if a['cat'] == cat['id']), key=lambda a: ORDEM_SEV.index(a['sev']))
        s.append(CondPageBreak(7 * cm))
        s.append(p(f'3.{i} {escape(cat["nome"])}', 'h2'))
        s.append(p(f'<b>Mecanismo na stack:</b> {escape(cat["stack"])}', 'pequeno'))
        s.append(Spacer(1, 4))
        cab = [p('Severidade', 'th'), p('Arquivo:linha', 'th'), p('Descrição', 'th')]
        linhas = [cab]
        for a in achados:
            desc = (f'<b>{a["id"]} — {escape(a["titulo"])}</b><br/>{escape(a["descricao"])}'
                    f'<br/><font color="{SUAVE}"><b>Condição:</b> {escape(a["condicao"])}</font>')
            linhas.append([chip_sev(a['sev']), _locais_celula(a), p(desc, 'celula')])
        s.append(tabela(linhas, [2.45 * cm, 6.35 * cm, UTIL - 8.8 * cm]))
        s.append(Spacer(1, 8))
        for a in achados:
            s.append(_cartao(a))
    return s


def secao_recomendacoes():
    s = [PageBreak(), p('4. Recomendações priorizadas', 'h1'),
         p('Ordem sugerida de execução. P1 fecha os três caminhos de alta severidade; cada item vira uma issue na seção 5.', 'suave')]
    cor = {'P1': PALETA['critica'], 'P2': PALETA['alta'], 'P3': PALETA['media'], 'P4': PALETA['baixa']}
    cab = [p('Prioridade', 'th'), p('Ações', 'th'), p('Achados', 'th')]
    linhas = [cab]
    for prio, prazo, itens, ids in dados.RECOMENDACOES:
        acoes = [p(f'<b>{escape(prazo)}</b>', 'celula_b')] + [p('• ' + escape(i), 'celula') for i in itens]
        linhas.append([Chip(prio, cor[prio], TINTA if prio == 'P3' else '#FFFFFF', tamanho=7.4), acoes,
                       p(escape(ids), 'celula_mono')])
    s.append(tabela(linhas, [2.2 * cm, UTIL - 5.2 * cm, 3.0 * cm]))
    return s


_MARCADOR = re.compile(r'^(\s*)(- \[ \] |- |\d+\. )')


def _quebrar_markdown(texto, largura=100):
    """Reflui a prosa (parágrafos e itens de lista) em até `largura` colunas.

    Blocos de código ficam como estão. Linhas que continuam um item de lista
    são juntadas ao item e quebradas com recuo pendente, o que mantém o
    Markdown válido ao copiar e colar.
    """
    saida, em_codigo, atual = [], False, None  # atual = [recuo_continuacao, texto]

    def descarregar():
        nonlocal atual
        if atual:
            saida.extend(textwrap.wrap(atual[1], largura, subsequent_indent=atual[0],
                                       break_long_words=False, break_on_hyphens=False))
        atual = None

    for linha in texto.strip('\n').split('\n'):
        limpa = linha.strip()
        if limpa.startswith('```'):
            descarregar()
            em_codigo = not em_codigo
            saida.append(linha)
        elif em_codigo:
            saida.append(linha)
        elif not limpa or limpa.startswith('#'):
            descarregar()
            saida.append(linha)
        elif (marca := _MARCADOR.match(linha)):
            descarregar()
            atual = [' ' * len(marca.group(0)), linha.rstrip()]
        elif atual is not None:
            atual[1] += ' ' + limpa
        else:
            atual = ['', limpa]
    descarregar()
    return '\n'.join(saida)


def texto_issue(issue):
    return f'Título: {issue["titulo"]}\nLabels sugeridas: {issue["labels"]}\n\n{_quebrar_markdown(issue["corpo"])}\n'


def gravar_issues_md(pasta=AQUI / 'issues'):
    """Mesmo texto das issues do PDF, em arquivos .md (cópia fiel, com linhas em branco)."""
    pasta.mkdir(exist_ok=True)
    for n, issue in enumerate(dados.ISSUES, start=1):
        (pasta / f'issue-{n:02d}.md').write_text(texto_issue(issue), encoding='utf-8')
    return pasta


def secao_issues():
    s = [PageBreak(), p('5. ISSUES PARA O GITHUB', 'h1'),
         p('Texto completo de cada issue, em Markdown, pronto para copiar e colar. Copie tudo o que está entre as linhas '
           '<font name="Mono">--- ISSUE n ---</font> e <font name="Mono">--- FIM ISSUE n ---</font>: a primeira linha é o '
           'título e a segunda, as labels sugeridas. Achados triviais do mesmo tema foram agrupados para não gerar issues demais. '
           'Alguns leitores de PDF descartam linhas em branco ao copiar; o Markdown abaixo continua válido sem elas, e o '
           'mesmo texto está em <font name="Mono">docs/security-audit/issues/issue-NN.md</font>.',
           'corpo')]
    resumo = [[p('#', 'th'), p('Título', 'th'), p('Achados', 'th')]] + [
        [p(str(n), 'celula_b'), p(escape(i['titulo']), 'celula'), p(escape(i['achados']), 'celula_mono')]
        for n, i in enumerate(dados.ISSUES, start=1)
    ]
    s.append(tabela(resumo, [0.8 * cm, UTIL - 4.6 * cm, 3.8 * cm]))
    for n, issue in enumerate(dados.ISSUES, start=1):
        s.append(CondPageBreak(9 * cm))
        s.append(p(f'Issue {n} — {escape(issue["achados"])}', 'h2'))
        texto = texto_issue(issue)
        s.append(p(f'--- ISSUE {n} ---', 'delim'))
        s.append(bloco_codigo(texto, 'issue'))
        s.append(p(f'--- FIM ISSUE {n} ---', 'delim'))
    return s


# ── Montagem ─────────────────────────────────────────────────────────────────


def gerar(saida=SAIDA):
    por_sev, por_cat, fortes = contagens()
    with tempfile.TemporaryDirectory() as tmp:
        graficos = {'rosca': Path(tmp) / 'rosca.png', 'barras': Path(tmp) / 'barras.png'}
        grafico_rosca(por_sev, graficos['rosca'])
        grafico_barras(por_cat, fortes, graficos['barras'])
        doc = SimpleDocTemplate(
            str(saida), pagesize=A4, leftMargin=MARGEM, rightMargin=MARGEM, topMargin=MARGEM, bottomMargin=MARGEM,
            title=dados.TITULO, author='Auditoria de segurança (Claude Code)', subject='Auditoria de segurança em 5 categorias',
            lang='pt-BR',
        )
        historia = (secao_capa() + secao_resumo(por_sev, fortes, graficos) + secao_fortes_fracos() + secao_achados()
                    + secao_recomendacoes() + secao_issues())
        doc.build(historia, onFirstPage=desenhar_capa, canvasmaker=CanvasNumerado)
    gravar_issues_md()
    return saida


def previa(pdf, pasta):
    import pypdfium2 as pdfium  # opcional: só para conferência visual

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    documento = pdfium.PdfDocument(str(pdf))
    total = len(documento)
    for i in range(total):
        pagina = documento[i]
        pagina.render(scale=1.4).to_pil().save(pasta / f'pagina-{i + 1:02d}.png')
        pagina.close()
    documento.close()
    return total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--saida', default=str(SAIDA))
    parser.add_argument('--previa', help='pasta para salvar cada página como PNG (requer pypdfium2)')
    args = parser.parse_args()
    arquivo = gerar(Path(args.saida))
    print(f'PDF gerado: {arquivo}')
    if args.previa:
        print(f'{previa(arquivo, args.previa)} páginas rasterizadas em {args.previa}')
