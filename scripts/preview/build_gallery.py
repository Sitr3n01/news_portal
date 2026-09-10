"""Index the unedited browser screenshots captured during local review."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / '.preview/evidence'


def picture(filename, label):
    if not (EVIDENCE / filename).is_file():
        raise FileNotFoundError(EVIDENCE / filename)
    return (
        f'<figure><figcaption>{escape(label)}</figcaption>'
        f'<a href="{filename}"><img src="{filename}" alt="{escape(label)}" loading="lazy"></a></figure>'
    )


sections = []
for label, slug in (
    ('Home', 'home'), ('Sobre', 'sobre'), ('Cursos', 'cursos'),
    ('Contato', 'contact'), ('Privacidade', 'privacidade'),
):
    sections.append(
        f'<section id="{slug}"><h2>{label} · 1440 px</h2><div class="pair">'
        + picture(f'before-{slug}-desktop-light.png', 'Antes')
        + picture(f'{slug}-desktop-light.png', 'Redesign · conteúdo atual')
        + '</div></section>'
    )
sections.append(
    '<section id="mobile"><h2>Home · 375 px</h2><div class="pair mobile">'
    + picture('before-home-mobile-light.png', 'Antes · celular')
    + picture('home-mobile-light.png', 'Redesign · celular')
    + '</div></section>'
)
sections.append('<section id="scenarios"><h2>Temas e cenários</h2><div class="pair">')
for filename, label in (
    ('home-desktop-dark.png', 'Home · tema escuro'),
    ('home-mobile-dark-en.png', 'Home · celular, inglês e tema escuro'),
    ('demo-testimonials-desktop.png', 'Depoimentos fictícios · com e sem imagem'),
    ('demo-social-desktop.png', 'Posts fictícios · imagem, fallback e vídeo'),
    ('contact-success-demo.png', 'Envio confirmado · somente banco experimental'),
    ('demo-cms-long-title-mobile.png', 'CMS · título longo em celular'),
):
    sections.append(picture(filename, label))
sections.append('</div></section>')
html = """<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Komuniki · comparação local</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:40px 24px;background:#e5e5e5;color:#111;font:16px/1.5 Arial,sans-serif}
main{max-width:1500px;margin:auto}h1{font-size:clamp(36px,5vw,64px);line-height:1;letter-spacing:-.04em}
h2{font-size:28px;margin:64px 0 24px}a{color:inherit;text-underline-offset:3px}
nav{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}nav a{background:#d1ffca;padding:8px 16px;border-radius:24px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}
figure{margin:0;background:#fff;border-radius:24px;overflow:hidden}figcaption{padding:16px 24px;font-weight:700}
img{display:block;width:100%;height:auto}.mobile{max-width:850px}
p{max-width:900px}.note{font-size:14px;color:#444}a:focus-visible{outline:3px solid #000;outline-offset:4px}
@media(max-width:800px){.pair{grid-template-columns:1fr}body{padding:24px 16px}}
</style><main><p>REVISÃO LOCAL · 08/09/2026</p><h1>KOMUNIKI<br>ANTES / DEPOIS</h1>
<p>Os mesmos conteúdos locais nas cinco páginas, agora com a apresentação editorial.
As imagens são capturas do navegador sem edição. Clique em uma captura para abrir seu tamanho completo.</p>
<p><a href="http://127.0.0.1:8011/">Abrir conteúdo atual redesenhado</a> ·
<a href="http://127.0.0.1:8012/">Abrir demonstração</a> ·
<a href="../../docs/technical/komuniki-editorial-preview.md">Instruções e matriz de preservação</a></p>
<nav aria-label="Capturas"><a href="#home">Home</a><a href="#sobre">Sobre</a>
<a href="#cursos">Cursos</a><a href="#contact">Contato</a><a href="#privacidade">Privacidade</a>
<a href="#mobile">Celular</a><a href="#scenarios">Temas e cenários</a></nav>
<p class="note">Os contatos de exemplo pertencem ao banco local. Os depoimentos e posts da demonstração
são fictícios e identificados na própria página. Nenhum conteúdo foi sincronizado com produção.</p>
""" + '\n'.join(sections) + '</main></html>'
destination = EVIDENCE / 'comparison.html'
destination.write_text(html, encoding='utf-8')
print(destination)
