/*
 * Newsroom — comportamento da casca do painel unificado.
 *
 * JavaScript simples, sem framework: gaveta da sidebar em telas pequenas,
 * menus suspensos (<details>), a alternância lista/grade e o clique na célula
 * inteira das caixas de seleção das listagens. Carregado na visão
 * geral, no Wagtail (insert_global_admin_js) e no Unfold (UNFOLD['SCRIPTS']).
 * Tudo funciona sem ele: a sidebar fica acessível pelo teclado, os <details>
 * abrem nativamente e a alternância de visualização cai para envio de formulário.
 */
(function () {
    'use strict';

    if (window.__newsroomShell) {
        return;
    }
    window.__newsroomShell = true;

    var VIEW_KEY = 'nr-view';
    var lastToggle = null;

    function sidebar() {
        return document.querySelector('[data-nr-sidebar]');
    }

    function backdrop() {
        return document.querySelector('[data-nr-backdrop]');
    }

    function setToggles(expanded) {
        document.querySelectorAll('[data-nr-menu-toggle]').forEach(function (button) {
            button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        });
    }

    function openMenu(trigger) {
        var panel = sidebar();
        if (!panel) {
            return;
        }
        lastToggle = trigger || null;
        panel.classList.add('is-open');
        var shade = backdrop();
        if (shade) {
            shade.hidden = false;
        }
        document.documentElement.classList.add('nr-menu-open');
        setToggles(true);
        var first = panel.querySelector('.nr-sidebar__close, a, button, summary');
        if (first) {
            first.focus();
        }
    }

    function closeMenu() {
        var panel = sidebar();
        if (!panel || !panel.classList.contains('is-open')) {
            return;
        }
        panel.classList.remove('is-open');
        var shade = backdrop();
        if (shade) {
            shade.hidden = true;
        }
        document.documentElement.classList.remove('nr-menu-open');
        setToggles(false);
        if (lastToggle) {
            lastToggle.focus();
        }
    }

    function closeDropdowns(except) {
        document.querySelectorAll('details[data-nr-dropdown][open]').forEach(function (details) {
            if (details !== except) {
                details.open = false;
            }
        });
    }

    document.addEventListener('click', function (event) {
        var toggle = event.target.closest('[data-nr-menu-toggle]');
        if (toggle) {
            event.preventDefault();
            var panel = sidebar();
            if (panel && panel.classList.contains('is-open')) {
                closeMenu();
            } else {
                openMenu(toggle);
            }
            return;
        }
        if (event.target.closest('[data-nr-menu-close]') || event.target.closest('[data-nr-backdrop]')) {
            closeMenu();
            return;
        }
        var owner = event.target.closest('details[data-nr-dropdown]');
        closeDropdowns(owner);
    });

    document.addEventListener('toggle', function (event) {
        var details = event.target;
        if (details.matches && details.matches('details[data-nr-dropdown]') && details.open) {
            closeDropdowns(details);
        }
    }, true);

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }
        var open = document.querySelector('details[data-nr-dropdown][open]');
        if (open) {
            open.open = false;
            var summary = open.querySelector('summary');
            if (summary) {
                summary.focus();
            }
            return;
        }
        closeMenu();
    });

    // Em telas largas a gaveta não existe: se a janela crescer com ela aberta,
    // desfaz o estado para não deixar o fundo escurecido.
    var wide = window.matchMedia('(min-width: 1024px)');
    var onWide = function (query) {
        if (query.matches) {
            closeMenu();
        }
    };
    if (wide.addEventListener) {
        wide.addEventListener('change', onWide);
    }

    // ── Lista ↔ grade ───────────────────────────────────────────────────────

    function storedView() {
        try {
            return window.localStorage.getItem(VIEW_KEY);
        } catch (error) {
            return null;
        }
    }

    function storeView(view) {
        try {
            window.localStorage.setItem(VIEW_KEY, view);
        } catch (error) {
            /* armazenamento indisponível: a preferência vale só para esta página */
        }
    }

    function withView(href, view) {
        try {
            var url = new URL(href, window.location.href);
            if (view === 'list') {
                url.searchParams.delete('view');
            } else {
                url.searchParams.set('view', view);
            }
            return url.pathname + url.search;
        } catch (error) {
            return href;
        }
    }

    function applyView(view, persist) {
        var list = document.querySelector('[data-nr-list]');
        if (list) {
            list.classList.toggle('is-grid', view === 'grid');
        }
        document.querySelectorAll('[data-nr-view]').forEach(function (button) {
            var active = button.getAttribute('data-nr-view') === view;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        var input = document.querySelector('[data-nr-view-input]');
        if (input) {
            input.value = view;
        }
        // Abas e paginação carregam a visualização atual no próprio link.
        document.querySelectorAll('#nr-tabs a[href], .nr-pagination a[href]').forEach(function (link) {
            link.setAttribute('href', withView(link.getAttribute('href'), view));
        });
        if (persist) {
            storeView(view);
            if (window.history && window.history.replaceState) {
                window.history.replaceState(window.history.state, '', withView(window.location.href, view));
            }
        }
    }

    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-nr-view]');
        if (!button) {
            return;
        }
        event.preventDefault();
        applyView(button.getAttribute('data-nr-view'), true);
    });

    function restoreView() {
        var params = new URLSearchParams(window.location.search);
        if (!params.has('view') && storedView() === 'grid' && document.querySelector('[data-nr-list]')) {
            applyView('grid', false);
        }
    }

    // O HTMX lê o destino dos links ao processá-los; aqui a requisição sai
    // sempre com a visualização atual, e a URL publicada no histórico também.
    document.addEventListener('htmx:configRequest', function (event) {
        var input = document.querySelector('[data-nr-view-input]');
        if (input && event.detail.verb === 'get' && event.detail.path) {
            event.detail.path = withView(event.detail.path, input.value || 'list');
        }
    });

    document.addEventListener('DOMContentLoaded', restoreView);
    document.addEventListener('htmx:afterSettle', function () {
        var input = document.querySelector('[data-nr-view-input]');
        if (input) {
            applyView(input.value || 'list', false);
        }
        closeDropdowns(null);
    });

    // ── Seleção nas listagens ──────────────────────────────────────────────
    // A caixa de seleção ocupa só 16–24px de uma célula bem maior: um clique
    // em qualquer ponto da célula marca e desmarca, como na própria caixa.
    // Wagtail (bulk-action-checkbox-cell / cabeçalho) e Django admin (Unfold).
    var CHECKBOX_CELLS = [
        'td.bulk-action-checkbox-cell',
        'th.bulk-actions-filter-checkbox',
        '#result_list td.action-checkbox',
        '#result_list th',
    ].join(', ');

    document.addEventListener('click', function (event) {
        var cell = event.target.closest(CHECKBOX_CELLS);
        if (!cell || event.target.closest('input, label, a, button, select')) {
            return;
        }
        var boxes = cell.querySelectorAll('input[type="checkbox"]');
        if (boxes.length === 1 && !boxes[0].disabled) {
            // Repassa o Shift: Wagtail e Django marcam um intervalo com Shift+clique.
            boxes[0].dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window,
                shiftKey: event.shiftKey,
            }));
        }
    });
})();
