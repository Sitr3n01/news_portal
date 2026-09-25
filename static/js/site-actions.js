/*
 * Ações declarativas do portal de notícias — no lugar dos onclick="..." inline.
 *
 * Atributo on* inline só roda com 'unsafe-inline' em script-src, e é essa
 * liberação que deixa um <script> ou onerror= injetado executar. Sem nenhum
 * handler inline nos templates, a CSP do site público exige nonce (ver
 * CONTENT_SECURITY_POLICY em config/settings/base.py).
 *
 * Tudo é delegado no document, na fase de CAPTURA: vale para o HTML que o HTMX
 * troca depois do carregamento (o botão de curtir, por exemplo) e roda antes
 * do listener de clique do próprio HTMX, que assim não dispara o POST quando a
 * ação é cancelada ou desviada.
 *
 *   data-confirm="Mensagem"      pede confirmação; cancelado, o clique não segue
 *   data-login-href="/url"       leva o visitante sem conta ao login
 *   data-share-title="Título"    Web Share API; sem ela, copia o link
 *   data-scroll-to="id"          rola suavemente até o elemento
 */
(function () {
    'use strict';

    var SELECTOR = '[data-confirm], [data-login-href], [data-share-title], [data-scroll-to]';

    function stop(event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    function share(title) {
        var url = window.location.href;
        if (navigator.share) {
            navigator.share({title: title, url: url}).catch(function () {});
            return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(function () {
                window.alert('Link copied!');
            }, function () {});
        }
    }

    document.addEventListener('click', function (event) {
        var element = event.target.closest(SELECTOR);
        if (!element) {
            return;
        }

        if (element.hasAttribute('data-confirm')) {
            if (!window.confirm(element.getAttribute('data-confirm'))) {
                stop(event);
            }
            return;
        }

        if (element.hasAttribute('data-login-href')) {
            stop(event);
            window.location.assign(element.getAttribute('data-login-href'));
            return;
        }

        if (element.hasAttribute('data-share-title')) {
            stop(event);
            share(element.getAttribute('data-share-title'));
            return;
        }

        var target = document.getElementById(element.getAttribute('data-scroll-to'));
        if (target) {
            stop(event);
            target.scrollIntoView({behavior: 'smooth'});
        }
    }, true);
})();
