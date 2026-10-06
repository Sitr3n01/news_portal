/**
 * Tailwind do site público da escola (Komuniki): páginas que estendem templates/base_school_editorial.html.
 * Saída: static/css/tailwind-school.css (npm run build:css:school).
 *
 * `theme` e `darkMode` reproduzem, valor por valor, o tailwind.config que ficava inline nesse template quando o Tailwind
 * rodava no navegador (Play CDN, static/js/vendor/tailwind.min.js). Mexeu aqui: rode `npm run build:css` e commite o CSS.
 *
 * Os caminhos de `content` valem a partir da raiz do repositório, que é onde o npm roda o script. Um template novo que
 * estenda a base da escola precisa cair em algum destes padrões, senão as classes dele não entram no CSS.
 */
module.exports = {
    darkMode: 'class',
    content: [
        './templates/base_school_editorial.html',
        './templates/school/**/*.html',
        './templates/contact/**/*.html',
        // Classes montadas em Python e em JS também contam. Testes, migrações e comandos nunca viram HTML de página.
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
            fontFamily: { sans: ['Inter', 'sans-serif'], display: ['Inter', 'sans-serif'] },
            maxWidth: { '7xl': '1200px' },
            colors: {
                primary: {
                    50: '#f3f3f3', 100: '#e5e5e5', 200: '#b8d8ff', 300: '#c6c6c6',
                    400: '#979797', 500: '#444444', 600: '#000000', 700: '#000000',
                    800: '#000000', 900: '#000000',
                },
            },
        },
    },
    plugins: [],
};
