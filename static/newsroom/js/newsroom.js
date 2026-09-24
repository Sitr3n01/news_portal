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
    var SIDEBAR_SCROLL_KEY = 'nr-sidebar-scroll';
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

    // Guarda a rolagem da sidebar ao sair da página; o script inline de
    // newsroom/partials/sidebar.html a devolve na página seguinte.
    window.addEventListener('pagehide', function () {
        var box = document.querySelector('[data-nr-sidebar-scroll]');
        if (!box) {
            return;
        }
        try {
            sessionStorage.setItem(SIDEBAR_SCROLL_KEY, String(Math.round(box.scrollTop)));
        } catch (error) {}
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }
        var open = document.querySelector('details[data-nr-dropdown][open]');
        if (open) {
            open.open = false;
            // O foco só volta para o botão do menu se estava dentro dele: com o
            // foco num campo do formulário, o Esc fecha o menu e o foco fica.
            var summary = open.querySelector('summary');
            if (summary && open.contains(document.activeElement)) {
                summary.focus();
            }
            return;
        }
        closeMenu();
    });

    // Menu aberto pelo teclado fecha quando o foco sai dele (Tab adiante).
    document.addEventListener('focusin', function (event) {
        document.querySelectorAll('details[data-nr-dropdown][open]').forEach(function (details) {
            if (!details.contains(event.target)) {
                details.open = false;
            }
        });
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

    // ── Barra de seleção (Django admin e Wagtail) e menu ⋯ das linhas ─────
    // A barra do Django admin fica em templates/admin/includes/selection_bar.html
    // e a do Wagtail em templates/wagtailadmin/bulk_actions/footer.html. O
    // actions.js do Django e o bulk-actions.js do Wagtail continuam donos da
    // seleção; aqui só entram o texto "N selecionados", o botão de limpar, o
    // nome da ação nos botões do Django e o menu ⋯ de cada linha.
    function adminBar() {
        return document.querySelector('.nr-selectionbar--admin');
    }

    // Wagtail: a barra vem no fim da página (era o rodapé fixo). Ela passa para
    // dentro do cabeçalho fixo da listagem e cobre título e busca enquanto há
    // seleção. O bulk-actions.js a acha pelo atributo, em qualquer lugar.
    function dockWagtailBar() {
        var bar = document.querySelector('.nr-selectionbar--wagtail');
        var header = bar && document.querySelector('main .w-slim-header');
        if (bar && header && bar.parentElement !== header) {
            header.appendChild(bar);
            bar.classList.add('is-docked');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', dockWagtailBar);
    } else {
        dockWagtailBar();
    }

    function adminBoxes() {
        return Array.prototype.slice.call(document.querySelectorAll('#result_list input.action-select'));
    }

    function updateAdminCount() {
        var bar = adminBar();
        var out = bar && bar.querySelector('[data-nr-selection-count]');
        if (!out) {
            return;
        }
        var count = adminBoxes().filter(function (box) {
            return box.checked;
        }).length;
        out.textContent = count === 1 ? '1 selecionado' : count + ' selecionados';
    }

    // Os scripts do Django marcam várias caixas de uma vez (Shift, "todos")
    // sem disparar eventos nelas: a contagem é refeita depois deles.
    ['change', 'click'].forEach(function (type) {
        document.addEventListener(type, function (event) {
            if (event.target.closest && event.target.closest('#result_list, [data-nr-selectionbar]')) {
                window.setTimeout(updateAdminCount, 0);
            }
        });
    });
    document.addEventListener('DOMContentLoaded', updateAdminCount);
    window.addEventListener('pageshow', function () {
        window.setTimeout(updateAdminCount, 0);
    });

    function clearSelection() {
        // Desmarca pelo clique em cada caixa, para que os scripts do Django e
        // do Wagtail atualizem contagem, rodapé e "selecionar todos".
        var checked = document.querySelectorAll(
            '#result_list input.action-select:checked, input[data-bulk-action-checkbox]:checked'
        );
        Array.prototype.forEach.call(checked, function (box) {
            box.click();
        });
    }

    document.addEventListener('click', function (event) {
        var action = event.target.closest('[data-nr-selectionbar] [data-nr-action]');
        if (action) {
            // Botão de ação do Django: envia o formulário com `index` e o nome
            // da ação no campo oculto, como o seletor do Unfold fazia.
            var input = action.closest('[data-nr-selectionbar]').querySelector('[data-nr-action-input]');
            if (input) {
                input.value = action.getAttribute('data-nr-action');
            }
            return;
        }
        if (event.target.closest('[data-nr-selection-clear]')) {
            event.preventDefault();
            clearSelection();
            return;
        }
        var rowAction = event.target.closest('[data-nr-row-action]');
        if (rowAction) {
            // Ação do menu ⋯: só esta linha marcada, depois o mesmo botão da barra.
            event.preventDefault();
            var bar = adminBar();
            var row = rowAction.closest('tr');
            var box = row && row.querySelector('input.action-select');
            var source = bar && bar.querySelector('[data-nr-action="' + rowAction.getAttribute('data-nr-row-action') + '"]');
            if (!box || !source) {
                return;
            }
            adminBoxes().forEach(function (other) {
                if (other !== box && other.checked) {
                    other.click();
                }
            });
            if (!box.checked) {
                box.click();
            }
            var across = bar.querySelector('input.select-across');
            if (across) {
                across.value = '0';
            }
            source.click();
        }
    });

    // As células da tabela do Unfold cortam o que passa da borda (overflow:
    // hidden): o menu ⋯ se posiciona na tela, alinhado ao botão, e abre para
    // cima quando não cabe embaixo. Rolar a página fecha o menu.
    function placeRowMenu(menu) {
        var panel = menu.querySelector('.nr-menu');
        var anchor = menu.querySelector('summary');
        if (!panel || !anchor) {
            return;
        }
        panel.style.position = 'fixed';
        panel.style.right = 'auto';
        var box = anchor.getBoundingClientRect();
        var width = panel.offsetWidth;
        var height = panel.offsetHeight;
        var left = Math.min(Math.max(8, box.right - width), window.innerWidth - width - 8);
        var top = box.bottom + 6;
        if (top + height > window.innerHeight - 8 && box.top - height - 6 > 8) {
            top = box.top - height - 6;
        }
        panel.style.left = left + 'px';
        panel.style.top = top + 'px';
    }

    ['scroll', 'resize'].forEach(function (type) {
        window.addEventListener(type, function () {
            document.querySelectorAll('details[data-nr-row-menu][open]').forEach(function (menu) {
                menu.open = false;
            });
        }, {passive: true, capture: true});
    });

    // ── Barra dos formulários do Django admin ─────────────────────────────
    // templates/admin/includes/form_bar.html. "Alterações não salvas" aparece
    // assim que algo muda no formulário, e sair da página com ela à vista pede
    // confirmação. Ctrl+S (Cmd+S no Mac) salva e continua na tela, como a
    // barra do editor do Wagtail; sem esse botão, só salva. E o formulário é
    // enviado uma vez só.
    function formBar() {
        return document.querySelector('[data-nr-formbar]');
    }

    function barForm() {
        var bar = formBar();
        return bar ? document.getElementById(bar.getAttribute('data-nr-form')) : null;
    }

    function dirtyNote() {
        var bar = formBar();
        return bar ? bar.querySelector('[data-nr-formbar-dirty]') : null;
    }

    function showDirty() {
        var note = dirtyNote();
        if (note) {
            note.hidden = false;
        }
    }

    function markDirty(event) {
        var form = barForm();
        var field = event.target;
        if (!form || !field || field.form !== form) {
            return;
        }
        // Campos sem nome (as buscas do seletor de grupos) não vão para o
        // servidor. As duas listas do seletor (select.filtered) mudam de seleção
        // só com o clique num item; o que conta é mover itens (mais abaixo).
        if (!field.name || (field.tagName === 'SELECT' && field.classList.contains('filtered'))) {
            return;
        }
        showDirty();
    }

    document.addEventListener('input', markDirty, true);
    document.addEventListener('change', markDirty, true);

    // Algo mudou em relação ao que veio do servidor? Para o que muda sem
    // evento: calendário e relógio dos campos de data (DateTimeShortcuts) e o
    // texto que o navegador devolve ao voltar para a página.
    function formChanged(form) {
        return Array.prototype.some.call(form.elements, function (field) {
            if (!field.name || field.disabled || /^(hidden|file|submit|button|reset)$/.test(field.type)) {
                return false;
            }
            if (field.tagName === 'SELECT') {
                if (field.classList.contains('filtered')) {
                    return false;
                }
                var options = Array.prototype.slice.call(field.options);
                if (field.type === 'select-one') {
                    // Sem opção marcada no HTML, o navegador mostra a primeira.
                    var initial = options.findIndex(function (option) { return option.defaultSelected; });
                    return field.selectedIndex !== Math.max(initial, 0);
                }
                return options.some(function (option) { return option.selected !== option.defaultSelected; });
            }
            if (field.type === 'checkbox' || field.type === 'radio') {
                return field.checked !== field.defaultChecked;
            }
            return field.value !== field.defaultValue;
        });
    }

    document.addEventListener('click', function (event) {
        if (!event.target.closest('.calendarbox, .clockbox, .datetimeshortcuts')) {
            return;
        }
        window.setTimeout(function () {
            var form = barForm();
            if (form && formChanged(form)) {
                showDirty();
            }
        }, 0);
    }, true);

    window.addEventListener('pageshow', function () {
        var entry = window.performance && performance.getEntriesByType && performance.getEntriesByType('navigation')[0];
        var form = barForm();
        if (form && entry && entry.type === 'back_forward' && formChanged(form)) {
            showDirty();
        }
    });

    // Depois do carregamento (ao montar os campos o próprio admin dispara
    // "change" pelo jQuery e o seletor de grupos preenche as listas):
    // - o select2 do autocompletar muda o campo com o jQuery do Django
    //   (.trigger), que não chega ao addEventListener;
    // - o seletor de grupos e permissões move os itens entre as listas sem
    //   evento nenhum: compara os itens escolhidos (SelectBox.cache, que não
    //   muda ao filtrar) com os do carregamento.
    window.addEventListener('load', function () {
        window.setTimeout(function () {
            var form = barForm();
            if (!form) {
                return;
            }
            if (window.django && window.django.jQuery) {
                window.django.jQuery(document).on('change', markDirty);
            }
            form.querySelectorAll('select.filtered[id$="_to"]').forEach(function (chosen) {
                var values = function () {
                    var cache = window.SelectBox && window.SelectBox.cache && window.SelectBox.cache[chosen.id];
                    var items = cache ? cache.map(function (item) { return String(item.value); }) :
                        Array.prototype.map.call(chosen.options, function (option) { return option.value; });
                    return items.sort().join('\n');
                };
                var initial = values();
                new MutationObserver(function () {
                    if (values() !== initial) {
                        showDirty();
                    }
                }).observe(chosen, {childList: true});
            });
        }, 0);
    });

    // Um envio por vez. Duplo clique, Enter duas vezes ou Ctrl+S repetido
    // enquanto o servidor responde criariam registros repetidos na tela de
    // adicionar. Se o envio for interrompido (botão Parar ou Esc do
    // navegador), a Navigation API avisa (navigateerror) e um novo envio vale
    // na hora; sem ela, depois de 10 s.
    var lastSubmit = 0;

    if (window.navigation && window.navigation.addEventListener) {
        window.navigation.addEventListener('navigateerror', function () {
            lastSubmit = 0;
        });
    }

    function submitting() {
        return lastSubmit && Date.now() - lastSubmit < 10000;
    }

    document.addEventListener('submit', function (event) {
        var form = barForm();
        if (!form || event.target !== form || event.defaultPrevented) {
            return;
        }
        if (submitting()) {
            event.preventDefault();
            return;
        }
        lastSubmit = Date.now();
    });

    window.addEventListener('pageshow', function () {
        lastSubmit = 0;
    });

    // Sair com "Alterações não salvas" à vista pede confirmação. O aviso do
    // Unfold só percebe digitação; este cobre também data escolhida no
    // calendário, autocompletar, seletor de grupos e a volta de um erro de
    // validação (a página chega com o que foi digitado e não salvo).
    window.addEventListener('beforeunload', function (event) {
        var note = dirtyNote();
        if (note && !note.hidden && !submitting()) {
            event.preventDefault();
            event.returnValue = '';
        }
    });

    document.addEventListener('keydown', function (event) {
        if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || (event.key || '').toLowerCase() !== 's') {
            return;
        }
        var bar = formBar();
        var button = bar && (bar.querySelector('button[name="_continue"]') || bar.querySelector('button[name="_save"]'));
        if (!button) {
            return;
        }
        event.preventDefault();
        if (event.repeat || submitting()) {
            return;
        }
        button.click();
    });

    // O menu ⋯ recebe as ações da barra (exceto remover, que já é um link
    // para a tela de confirmação) na primeira vez em que abre.
    document.addEventListener('toggle', function (event) {
        var menu = event.target;
        if (!menu.matches || !menu.matches('details[data-nr-row-menu]') || !menu.open) {
            return;
        }
        var slot = menu.querySelector('[data-nr-row-actions]');
        var bar = adminBar();
        if (slot && bar && !slot.childElementCount) {
            bar.querySelectorAll('[data-nr-action]').forEach(function (source) {
                var name = source.getAttribute('data-nr-action');
                if (name === 'delete_selected') {
                    return;
                }
                var item = document.createElement('button');
                item.type = 'button';
                item.className = 'nr-menu__item';
                item.setAttribute('data-nr-row-action', name);
                item.textContent = source.textContent.replace(/\s+/g, ' ').trim();
                slot.appendChild(item);
            });
        }
        placeRowMenu(menu);
    }, true);
})();
