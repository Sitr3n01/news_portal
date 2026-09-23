/*
 * Newsroom — arrastar para reordenar os blocos do StreamField.
 *
 * O Wagtail 7.4 já cria um SortableJS em cada lista de blocos (StreamBlock e
 * ListBlock), com a alça ⠿ do cabeçalho do bloco como único ponto de pega.
 * Este arquivo só ajusta aquela instância; não há biblioteca nova. Carregado
 * pelo hook `insert_editor_js` (apps/common/wagtail_hooks.py), ou seja, só nos
 * formulários de criação e edição.
 *
 * 1. Pega: com mouse, o bloco inteiro é arrastado pela barra de título; com o
 *    dedo ou a caneta, só pela alça, porque o resto do cabeçalho precisa
 *    continuar rolando a página. A troca acontece a cada toque, antes de o
 *    SortableJS decidir se começa o arraste.
 *
 * 2. Posição: o Wagtail traduz o arraste em `moveBlock(de, para)` usando os
 *    índices do SortableJS, que contam também os blocos excluídos (eles ficam
 *    na página, ocultos, até salvar). Depois de excluir um bloco, arrastar
 *    outro gravava uma ordem diferente da que aparece na tela. Aqui os dois
 *    índices vêm da lista de blocos vivos do próprio Wagtail.
 *
 * 3. Arraste em andamento: `html.nr-sf-dragging` desliga o ponteiro no
 *    conteúdo dos blocos (texto rico, tabela, campos), para o bloco só cair
 *    ENTRE blocos. A rolagem automática perto da borda fica mais generosa.
 *
 * Depende de detalhes internos do Wagtail (`initDragNDrop`, `sortable`,
 * `children`, `inserters`, `moveBlock`). Se algum sumir numa atualização, o
 * script não faz nada e o arraste nativo continua funcionando. Ao atualizar o
 * Wagtail, confira docs/technical/PAINEL_UNIFICADO.md §8.
 */
(function () {
    'use strict';

    if (window.__newsroomStreamfield) {
        return;
    }
    window.__newsroomStreamfield = true;

    var FLAG = '__nrStreamfield';
    var DRAGGING_CLASS = 'nr-sf-dragging';
    // Alça nativa do Wagtail (botão ⠿ no cabeçalho de cada bloco).
    var GRIP = '[data-streamfield-action="DRAG"]';
    // Barra de título do próprio bloco. O `>` garante que o cabeçalho de um
    // bloco aninhado não arraste o bloco de fora.
    var HEADER = '[data-streamfield-child] > section > .w-panel__header';
    // Os demais botões e links do cabeçalho (subir, descer, duplicar, excluir,
    // âncora) continuam só clicáveis.
    var NOT_A_HANDLE = '[data-streamfield-action]:not(' + GRIP + '), .w-panel__anchor';

    var sortables = [];

    function prefersReducedMotion() {
        return Boolean(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }

    function indexOfElement(items, element) {
        for (var i = 0; i < items.length; i++) {
            if (items[i] && items[i].element === element) {
                return i;
            }
        }
        return -1;
    }

    // Aplica o arraste que o SortableJS acabou de fazer no DOM à lista de
    // blocos do Wagtail, que é quem grava os campos `<prefixo>-N-order`.
    function reorder(sequence, item) {
        var children = sequence.children;
        var from = indexOfElement(children, item);
        if (from < 0) {
            return;
        }
        var to = 0;
        for (var node = item.previousElementSibling; node; node = node.previousElementSibling) {
            if (indexOfElement(children, node) >= 0) {
                to++;
            }
        }
        if (from !== to) {
            sequence.moveBlock(from, to);
            return;
        }
        // Mesma posição entre os blocos vivos, mas o SortableJS pode ter
        // largado o bloco do outro lado de um bloco excluído: volta para logo
        // depois do seu botão "+".
        var inserter = sequence.inserters && sequence.inserters[from];
        var anchor = inserter && inserter.element;
        if (anchor && anchor.parentNode === item.parentNode && anchor.nextElementSibling !== item) {
            anchor.parentNode.insertBefore(item, anchor.nextSibling);
        }
    }

    function enhance(sequence) {
        var sortable = sequence && sequence.sortable;
        if (!sortable || sortable[FLAG] || typeof sortable.option !== 'function'
            || typeof sequence.moveBlock !== 'function' || !sequence.children) {
            return;
        }
        sortable[FLAG] = true;
        sortables.push(sortable);

        sortable.option('handle', HEADER);
        sortable.option('filter', NOT_A_HANDLE);
        // Sem isto o SortableJS cancelaria o clique nos botões filtrados.
        sortable.option('preventOnFilter', false);
        sortable.option('scrollSensitivity', 80);
        sortable.option('scrollSpeed', 16);
        if (prefersReducedMotion()) {
            sortable.option('animation', 0);
        }
        sortable.option('onStart', function () {
            document.documentElement.classList.add(DRAGGING_CLASS);
        });
        sortable.option('onEnd', function (event) {
            document.documentElement.classList.remove(DRAGGING_CLASS);
            reorder(sequence, event.item);
        });
    }

    // Percorre uma árvore de blocos já montada atrás de listas (StreamBlock ou
    // ListBlock, inclusive aninhadas dentro de StructBlock).
    function walk(block, depth) {
        if (!block || depth > 25) {
            return;
        }
        if (block.sortable) {
            enhance(block);
        }
        var i;
        if (block.children && block.children.length) {
            for (i = 0; i < block.children.length; i++) {
                walk(block.children[i] && block.children[i].block, depth + 1);
            }
        }
        if (block.childBlocks && typeof block.childBlocks === 'object') {
            var names = Object.keys(block.childBlocks);
            for (i = 0; i < names.length; i++) {
                walk(block.childBlocks[names[i]], depth + 1);
            }
        }
    }

    function scan() {
        var roots = document.querySelectorAll('[id$="-root"]');
        for (var i = 0; i < roots.length; i++) {
            if (roots[i].rootBlock) {
                walk(roots[i].rootBlock, 0);
            }
        }
    }

    // Toda lista criada daqui em diante (ao carregar o formulário ou ao
    // inserir um bloco que contém outra lista) passa por `initDragNDrop`.
    function patchPrototypes() {
        var blocks = window.wagtailStreamField && window.wagtailStreamField.blocks;
        if (!blocks) {
            return;
        }
        [blocks.StreamBlock, blocks.ListBlock].forEach(function (cls) {
            var proto = cls && cls.prototype;
            while (proto && !Object.prototype.hasOwnProperty.call(proto, 'initDragNDrop')) {
                proto = Object.getPrototypeOf(proto);
            }
            if (!proto || typeof proto.initDragNDrop !== 'function' || proto.initDragNDrop[FLAG]) {
                return;
            }
            var original = proto.initDragNDrop;
            var patched = function () {
                var result = original.apply(this, arguments);
                enhance(this);
                return result;
            };
            patched[FLAG] = true;
            proto.initDragNDrop = patched;
        });
    }

    // Antes de o SortableJS ver o toque (ele escuta `pointerdown` na lista, na
    // fase de borbulha), escolhe a pega conforme o tipo de ponteiro.
    document.addEventListener('pointerdown', function (event) {
        var handle = event.pointerType === 'touch' || event.pointerType === 'pen' ? GRIP : HEADER;
        for (var i = 0; i < sortables.length; i++) {
            sortables[i].option('handle', handle);
        }
    }, true);

    patchPrototypes();
    scan();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scan);
    }
    window.addEventListener('load', scan);
}());
