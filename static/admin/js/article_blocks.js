// Mostra apenas os campos relevantes ao tipo de bloco escolhido, deixando a
// edição de blocos de artigo amigável (sem campos irrelevantes na tela).
//
// Cada campo é amarrado à sua linha pelo prefixo do "name" (ex.: blocks-0-media),
// então o toggle funciona por linha independentemente da marcação do Unfold.
(function () {
    'use strict';

    var FIELD_KEYS = ['rich_text', 'media', 'embed_url', 'caption'];

    function sectionFor(prefix, field) {
        var el = document.querySelector('[name="' + prefix + '-' + field + '"]');
        if (!el) {
            return null;
        }
        return el.closest('.block-fields') || el.closest('fieldset');
    }

    function shouldShow(field, type) {
        if (field === 'rich_text') { return type === 'rich_text'; }
        if (field === 'media') { return type === 'image'; }
        if (field === 'embed_url') { return type === 'embed'; }
        if (field === 'caption') { return type === 'image' || type === 'embed'; }
        return true;
    }

    function refresh(select) {
        var name = select.getAttribute('name') || '';
        var prefix = name.replace(/-block_type$/, '');
        if (prefix === name) {
            return;
        }
        var type = select.value;
        FIELD_KEYS.forEach(function (field) {
            var section = sectionFor(prefix, field);
            if (section) {
                section.style.display = shouldShow(field, type) ? '' : 'none';
            }
        });
    }

    function bind(select) {
        // Pula a linha-modelo do Django (__prefix__): só as cópias reais contam.
        if ((select.name || '').indexOf('__prefix__') !== -1) {
            return;
        }
        // Marca via propriedade JS (não atributo): cloneNode copia atributos mas
        // NÃO propriedades, então blocos recém-adicionados (clones do template)
        // sempre recebem o próprio listener em vez de parecerem "já vinculados".
        if (select.blockBound) {
            return;
        }
        select.blockBound = true;
        select.addEventListener('change', function () { refresh(select); });
        refresh(select);
    }

    function initAll() {
        document.querySelectorAll('select[name$="-block_type"]').forEach(bind);
    }

    if (document.readyState !== 'loading') {
        initAll();
    } else {
        document.addEventListener('DOMContentLoaded', initAll);
    }

    // Novo bloco adicionado via "Adicionar outro" (evento nativo do admin do Django).
    document.addEventListener('formset:added', initAll);
})();
