/**
 * Tailwind do portal de notícias (Blog da Kelly, em /news/): páginas que estendem templates/base_news.html, o que inclui
 * as telas de conta (templates/accounts/) e de acesso (templates/auth/, via auth/base_auth.html).
 * Saída: static/css/tailwind-news.css (npm run build:css:news).
 *
 * `theme`, `darkMode` e plugins reproduzem, valor por valor, o tailwind.config que ficava inline em base_news.html quando o
 * Tailwind rodava no navegador (Play CDN com plugins, static/js/vendor/tailwind.forms-cq.min.js). Aquele build embutia
 * @tailwindcss/forms 0.5.9 (o mesmo código da 0.5.10) e @tailwindcss/container-queries 0.1.x; o line-clamp já é do núcleo
 * desde o Tailwind 3.3. Mexeu aqui: rode `npm run build:css` e commite o CSS.
 *
 * Os caminhos de `content` valem a partir da raiz do repositório, que é onde o npm roda o script. Um template novo que
 * estenda a base do portal precisa cair em algum destes padrões, senão as classes dele não entram no CSS.
 */
module.exports = {
    darkMode: 'class',
    content: [
        './templates/base_news.html',
        './templates/news/**/*.html',
        // news/wagtail e news/email são telas do Wagtail e e-mail: não passam pelo Tailwind do portal.
        '!./templates/news/wagtail/**',
        '!./templates/news/email/**',
        './templates/accounts/**/*.html',
        './templates/auth/**/*.html',
        './templates/components/**/*.html',
        // Classes montadas em Python (HTML devolvido ao HTMX, widgets de formulário) e em JS também contam. Testes,
        // migrações e comandos nunca viram HTML de página.
        './apps/**/*.py',
        '!./apps/**/migrations/**',
        '!./apps/**/management/**',
        '!./apps/**/test_*.py',
        '!./apps/**/tests.py',
        './static/js/**/*.js',
        '!./static/js/vendor/**',
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#eef2ff',
                    100: '#dce5ff',
                    200: '#b9ccfe',
                    300: '#8baafe',
                    400: '#5882fd',
                    500: '#1152d4',
                    600: '#1152d4',
                    700: '#163ca8',
                    800: '#112e82',
                    900: '#082868',
                    DEFAULT: '#1152d4',
                },
                'background-light': '#ffffff',
                // Preto puro, como o site da escola. Só o escuro usa este token.
                'background-dark': '#000000',
                'slate-900': '#1a1a1a',
                'slate-500': '#6b7280',
            },
            fontFamily: {
                display: ['Newsreader', 'serif'],
                sans: ['Inter', 'sans-serif'],
                ui: ['Inter', 'sans-serif'],
            },
            borderRadius: { DEFAULT: '0.25rem', lg: '0.5rem', xl: '0.75rem', full: '9999px' },
        },
    },
    plugins: [require('@tailwindcss/forms'), require('@tailwindcss/container-queries')],
};
