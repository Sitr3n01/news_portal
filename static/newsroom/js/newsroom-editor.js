/*
 * Newsroom — ações de publicação na barra única do editor.
 *
 * A barra (templates/newsroom/editor/header.html) fica fora do formulário, e
 * os botões de salvar, publicar e enviar para moderação precisam continuar
 * DENTRO dele: o Wagtail só aplica a proteção de edição simultânea (aviso de
 * que outra pessoa salvou uma versão mais nova) aos botões do formulário. Por
 * isso o rodapé nativo continua na página, oculto, e este script cria na barra
 * botões que só clicam nos nativos. Spinner, "Publicando…", bloqueio e modais
 * de moderação continuam sendo do Wagtail; a barra só espelha o estado.
 *
 * Arrumação:
 * - principal (preto): o passo que leva a matéria adiante: aprovar, publicar
 *   ou enviar para moderação, nessa ordem de preferência;
 * - "Salvar rascunho" ao lado, como secundário (sem espaço, vai para o menu);
 * - o resto (retirar do ar, cancelar moderação, outras ações de moderação) no
 *   menu da seta, com as destrutivas por último.
 *
 * Carregado pelo hook `insert_editor_js` (apps/common/wagtail_hooks.py). Sem a
 * barra na página, ou se os botões nativos mudarem de forma, não faz nada e o
 * rodapé do Wagtail continua visível.
 */
(function () {
    'use strict';

    if (window.__newsroomEditorBar) {
        return;
    }
    window.__newsroomEditorBar = true;

    var READY_CLASS = 'nr-editorbar-ready';
    var PRIMARY_ORDER = ['approve', 'action-publish', 'action-submit', 'action-restart-workflow'];
    var DANGER = {'action-unpublish': true, 'action-cancel-workflow': true};
    var ICONS = {
        'save': 'save',
        'action-publish': 'upload',
        'action-submit': 'send',
        'action-restart-workflow': 'send',
        'approve': 'check',
        'workflow': 'edit',
        'action-unpublish': 'eye-off',
        'action-cancel-workflow': 'close',
        'locked': 'lock'
    };
    // Rótulos curtos para telas estreitas; o nome completo fica no `title`.
    var SHORT = {
        'save': 'Salvar',
        'action-submit': 'Enviar',
        'action-restart-workflow': 'Reenviar',
        'approve': 'Aprovar'
    };

    function spriteUrl() {
        var use = document.querySelector('svg.nr-icon use');
        var href = use && (use.getAttribute('href') || use.getAttribute('xlink:href'));
        return href ? href.split('#')[0] : '';
    }

    var SPRITE = '';

    function icon(name) {
        var ns = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('class', 'nr-icon');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        var use = document.createElementNS(ns, 'use');
        use.setAttribute('href', SPRITE + '#nr-' + name);
        svg.appendChild(use);
        return svg;
    }

    function kindOf(element) {
        var workflow = element.getAttribute('data-workflow-action-name');
        if (workflow) {
            return workflow === 'approve' ? 'approve' : 'workflow';
        }
        var name = element.getAttribute('name');
        if (name) {
            return name;
        }
        if (element.tagName === 'A') {
            return /\/unpublish\//.test(element.getAttribute('href') || '') ? 'action-unpublish' : 'link';
        }
        if (element.getAttribute('data-w-kbd-key-value') === 'mod+s') {
            return 'save';
        }
        return element.disabled ? 'locked' : 'other';
    }

    function labelOf(element) {
        var target = element.querySelector('[data-w-progress-target="label"]') || element;
        return (target.textContent || '').replace(/\s+/g, ' ').trim();
    }

    // Calculado uma vez, com o rótulo em repouso: durante o envio o nativo vira
    // "Agendando…"/"Publicando…", e o rótulo curto não pode trocar de sentido.
    function shortLabel(kind, label) {
        if (kind === 'action-publish') {
            return /^(agend|schedul)/i.test(label) ? 'Agendar' : 'Publicar';
        }
        return SHORT[kind] || '';
    }

    function isLoading(element) {
        return element.classList.contains('button-longrunning-active')
            || element.getAttribute('data-w-progress-loading-value') === 'true';
    }

    function closeMenu(from) {
        var details = from.closest('details');
        if (details) {
            details.open = false;
        }
    }

    // Desenha o conteúdo do botão da barra a partir do estado atual do nativo.
    function paint(proxy, control) {
        var real = control.element;
        var label = labelOf(real);
        var short = control.short;
        while (proxy.firstChild) {
            proxy.removeChild(proxy.firstChild);
        }
        proxy.appendChild(icon(ICONS[control.kind] || 'arrow'));
        var full = document.createElement('span');
        full.className = 'nr-editorbar__label';
        full.textContent = label;
        proxy.appendChild(full);
        if (short && short !== label && !proxy.classList.contains('nr-menu__item')) {
            full.classList.add('nr-editorbar__label--full');
            var brief = document.createElement('span');
            brief.className = 'nr-editorbar__label nr-editorbar__label--short';
            brief.setAttribute('aria-hidden', 'true');
            brief.textContent = short;
            proxy.appendChild(brief);
            proxy.title = label;
            // Nome acessível sempre completo, qualquer que seja o rótulo visível.
            proxy.setAttribute('aria-label', label);
        }
        if (control.kind === 'save') {
            proxy.setAttribute('aria-keyshortcuts', 'Control+S Meta+S');
            proxy.title = label + ' (Ctrl+S)';
        }
        if (real.tagName !== 'A') {
            proxy.disabled = real.disabled;
            proxy.classList.toggle('is-loading', isLoading(real));
        }
    }

    function makeControl(control, className) {
        var real = control.element;
        var isLink = real.tagName === 'A';
        var proxy = document.createElement(isLink ? 'a' : 'button');
        proxy.className = className;
        proxy.setAttribute('data-nr-action', control.kind);
        if (DANGER[control.kind]) {
            proxy.classList.add('is-danger');
        }
        if (isLink) {
            proxy.href = real.getAttribute('href');
        } else {
            proxy.type = 'button';
            proxy.addEventListener('click', function (event) {
                event.preventDefault();
                closeMenu(proxy);
                if (!real.disabled) {
                    // Clique no botão nativo: submete o formulário com ele
                    // como remetente e passa pelos controladores do Wagtail.
                    real.click();
                }
            });
            new MutationObserver(function () {
                paint(proxy, control);
            }).observe(real, {attributes: true, childList: true, characterData: true, subtree: true});
        }
        paint(proxy, control);
        return proxy;
    }

    function pickPrimary(controls) {
        for (var i = 0; i < PRIMARY_ORDER.length; i++) {
            for (var j = 0; j < controls.length; j++) {
                if (controls[j].kind === PRIMARY_ORDER[i]) {
                    return controls[j];
                }
            }
        }
        return controls[0];
    }

    // ── Barra que se ajusta à largura ────────────────────────────────────
    // Com a barra em duas linhas (título em cima, ferramentas e ações
    // embaixo), a linha de baixo mostra o que couber, na ordem de importância
    // de FIT_ORDER; o que não couber vai para o botão ⋯ ("Mais ferramentas")
    // da própria fileira. "Salvar rascunho" é o único que vai para outro lugar:
    // o menu da seta do publicar, onde já ficava no celular. Em uma linha só
    // (barra larga), tudo fica à vista. Sem este script, a linha só quebra.
    var HIDDEN = 'is-nr-overflowed';
    var FIT_ORDER = [
        '[data-side-panel-toggle="preview"]',
        '[data-side-panel-toggle="checks"]',
        '.nr-editorbar__save',
        '.nr-editorbar__history',
        '#nr-editorbar-quick a',
        '.nr-editorbar__remove'
    ];

    function fitCandidates(bar) {
        var found = [];
        FIT_ORDER.forEach(function (selector) {
            bar.querySelectorAll(selector).forEach(function (element) {
                if (found.indexOf(element) < 0) {
                    found.push(element);
                }
            });
        });
        return found;
    }

    function sameLine(a, b) {
        var first = a.getBoundingClientRect();
        var second = b.getBoundingClientRect();
        return Math.abs((first.top + first.height / 2) - (second.top + second.height / 2)) < first.height / 2;
    }

    function fitBar(bar) {
        var start = bar.querySelector('.nr-editorbar__start');
        var end = bar.querySelector('.nr-editorbar__end');
        var tools = bar.querySelector('.nr-editorbar__tools');
        var commit = bar.querySelector('.nr-editorbar__commit');
        var overflow = bar.querySelector('.nr-editorbar__overflow');
        if (!start || !end || !tools || !commit || !overflow) {
            return;
        }
        var candidates = fitCandidates(bar);
        var save = bar.querySelector('.nr-editorbar__save');
        var fits = function () {
            return end.scrollWidth <= end.clientWidth + 1 && sameLine(tools, commit);
        };

        candidates.forEach(function (element) {
            element.classList.remove(HIDDEN);
        });
        bar.classList.remove('is-nr-save-in-menu');
        overflow.hidden = true;
        if (sameLine(start, end) || fits()) {
            return;
        }

        // Tudo recolhido, depois de volta um a um, na ordem de importância,
        // enquanto couber. Um item grande que não cabe não impede um menor.
        overflow.hidden = false;
        candidates.forEach(function (element) {
            element.classList.add(HIDDEN);
        });
        bar.classList.add('is-nr-save-in-menu');
        candidates.forEach(function (element) {
            element.classList.remove(HIDDEN);
            if (element === save) {
                bar.classList.remove('is-nr-save-in-menu');
            }
            if (!fits()) {
                element.classList.add(HIDDEN);
                if (element === save) {
                    bar.classList.add('is-nr-save-in-menu');
                }
            }
        });
        var inOverflow = candidates.some(function (element) {
            return element !== save && element.classList.contains(HIDDEN);
        });
        if (!inOverflow) {
            overflow.hidden = true;
        }
    }

    function overflowItem(source, className) {
        var isLink = source.tagName === 'A';
        var item = document.createElement(isLink ? 'a' : 'button');
        item.className = className;
        if (isLink) {
            item.href = source.getAttribute('href');
        } else {
            item.type = 'button';
            item.addEventListener('click', function () {
                closeMenu(item);
                source.click();
            });
        }
        var drawing = source.querySelector('svg');
        if (drawing) {
            var copy = drawing.cloneNode(true);
            copy.setAttribute('class', 'nr-icon');
            item.appendChild(copy);
        }
        var named = source.querySelector('.w-side-panel-toggle__label, .nr-editorbar__label');
        var text = document.createElement('span');
        text.textContent = (named && named.textContent.trim()) || source.getAttribute('aria-label') || '';
        item.appendChild(text);
        return item;
    }

    // O menu ⋯ é montado a cada abertura, com o que está recolhido naquele
    // momento; remover vem por último, separado.
    function fillOverflow(bar, menu) {
        menu.textContent = '';
        var hidden = fitCandidates(bar).filter(function (element) {
            return element.classList.contains(HIDDEN) && !element.classList.contains('nr-editorbar__save');
        });
        hidden.forEach(function (element) {
            var danger = element.classList.contains('nr-editorbar__remove');
            if (danger && menu.childElementCount) {
                var divider = document.createElement('hr');
                divider.className = 'nr-menu__divider';
                menu.appendChild(divider);
            }
            menu.appendChild(overflowItem(element, 'nr-menu__item' + (danger ? ' is-danger' : '')));
        });
        // O botão fica no meio da barra: o menu não pode sair da tela.
        menu.style.left = '0px';
        var box = menu.getBoundingClientRect();
        var shift = Math.min(0, window.innerWidth - 12 - box.right) + Math.max(0, 12 - box.left);
        menu.style.left = shift + 'px';
    }

    function setupFit(bar) {
        var tools = bar.querySelector('.nr-editorbar__tools');
        var end = bar.querySelector('.nr-editorbar__end');
        if (!tools || !end) {
            return;
        }
        var overflow = document.createElement('details');
        overflow.className = 'nr-editorbar__overflow';
        overflow.setAttribute('data-nr-dropdown', '');
        overflow.hidden = true;
        var summary = document.createElement('summary');
        summary.className = 'w-side-panel-toggle nr-editorbar__overflow-button';
        summary.setAttribute('aria-label', 'Mais ferramentas');
        summary.appendChild(icon('ellipsis'));
        overflow.appendChild(summary);
        var menu = document.createElement('div');
        menu.className = 'nr-menu nr-editorbar__overflow-menu';
        overflow.appendChild(menu);
        overflow.addEventListener('toggle', function () {
            if (overflow.open) {
                fillOverflow(bar, menu);
            }
        });
        tools.appendChild(overflow);
        bar.setAttribute('data-nr-fit', '');

        var queued = false;
        var refit = function () {
            if (queued) {
                return;
            }
            queued = true;
            // setTimeout, não requestAnimationFrame: com a aba oculta o rAF para.
            window.setTimeout(function () {
                queued = false;
                if (!overflow.open) {
                    fitBar(bar);
                }
            }, 0);
        };
        var width = 0;
        new ResizeObserver(function (entries) {
            var current = Math.round(entries[0].contentRect.width);
            if (current !== width) {
                width = current;
                refit();
            }
        }).observe(bar);
        // O salvamento automático troca pedaços da barra (Publicação, ícones,
        // remover), e a largura deles muda. As mudanças dentro do próprio ⋯
        // (o menu montado a cada abertura) não contam.
        new MutationObserver(function (changes) {
            var outside = changes.some(function (change) {
                return !overflow.contains(change.target);
            });
            if (outside) {
                refit();
            }
        }).observe(end, {childList: true, subtree: true});
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(refit);
        }
        fitBar(bar);
    }

    function build() {
        var bar = document.querySelector('[data-nr-editorbar]');
        var slot = bar && bar.querySelector('[data-nr-editor-actions]');
        var form = document.querySelector('form[data-edit-form]');
        var nav = form && form.querySelector('footer .actions');
        if (!slot || !nav) {
            return;
        }
        var controls = Array.prototype.filter.call(nav.querySelectorAll('button, a'), function (element) {
            return !element.classList.contains('w-dropdown__toggle');
        }).map(function (element) {
            var kind = kindOf(element);
            return {element: element, kind: kind, short: shortLabel(kind, labelOf(element))};
        });
        if (!controls.length) {
            return;
        }
        SPRITE = spriteUrl();

        var primary = pickPrimary(controls);
        var save = null;
        controls.forEach(function (control) {
            if (control.kind === 'save' && control !== primary) {
                save = control;
            }
        });
        var others = controls.filter(function (control) {
            return control !== primary && control !== save;
        });
        others.sort(function (a, b) {
            return (DANGER[a.kind] ? 1 : 0) - (DANGER[b.kind] ? 1 : 0);
        });

        if (save) {
            slot.appendChild(makeControl(save, 'nr-btn nr-btn--secondary nr-editorbar__save'));
        }

        var group = document.createElement('div');
        group.className = 'nr-editorbar__split';
        group.appendChild(makeControl(primary, 'nr-btn nr-btn--primary nr-editorbar__primary'));

        if (others.length || save) {
            var details = document.createElement('details');
            details.className = 'nr-editorbar__menu' + (others.length ? '' : ' is-narrow-only');
            details.setAttribute('data-nr-dropdown', '');
            var summary = document.createElement('summary');
            summary.className = 'nr-btn nr-btn--primary nr-editorbar__caret';
            summary.setAttribute('aria-label', 'Mais ações de publicação');
            summary.appendChild(icon('down'));
            details.appendChild(summary);
            var menu = document.createElement('div');
            menu.className = 'nr-menu nr-menu--right';
            if (save) {
                // Quando não cabe na barra (fitBar), o "Salvar rascunho" vem para cá.
                menu.appendChild(makeControl(save, 'nr-menu__item nr-editorbar__menu-save'));
            }
            others.forEach(function (control, index) {
                var previous = others[index - 1];
                if (DANGER[control.kind] && !(previous && DANGER[previous.kind]) && (index > 0 || save)) {
                    // Separa as destrutivas. Se só o "Salvar" (do celular)
                    // vem antes, o separador também só aparece no celular.
                    var divider = document.createElement('hr');
                    divider.className = 'nr-menu__divider' + (index > 0 ? '' : ' nr-editorbar__menu-save');
                    menu.appendChild(divider);
                }
                menu.appendChild(makeControl(control, 'nr-menu__item'));
            });
            details.appendChild(menu);
            group.appendChild(details);
        }

        slot.appendChild(group);
        document.documentElement.classList.add(READY_CLASS);
        if (window.ResizeObserver) {
            setupFit(bar);
        }
    }

    // O controle "Publicação" (newsroom/editor/_publication.html) só clica nos
    // controles do painel "Status" do Wagtail: a janela de agendamento, a trava
    // e o próprio botão do painel. O controle é reenviado pelo salvamento
    // automático, por isso a delegação no documento.
    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-nr-proxy-click]');
        if (!trigger) {
            return;
        }
        var target = document.querySelector(trigger.getAttribute('data-nr-proxy-click'));
        var dropdown = trigger.closest('details[open]');
        if (dropdown) {
            dropdown.open = false;
        }
        if (target) {
            event.preventDefault();
            target.click();
        }
    });

    try {
        build();
    } catch (error) {
        // Qualquer falha deixa o rodapé nativo do Wagtail à vista.
        document.documentElement.classList.remove(READY_CLASS);
        if (window.console) {
            window.console.error('newsroom-editor:', error);
        }
    }
}());
