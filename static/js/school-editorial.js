document.addEventListener('alpine:init', () => {
    const readPreference = (key, fallback) => {
        try { return localStorage.getItem(key) || fallback; } catch (_) { return fallback; }
    };
    const savePreference = (key, value) => {
        try { localStorage.setItem(key, value); } catch (_) { /* Private browsing remains usable. */ }
    };
    Alpine.data('schoolEditorial', () => ({
        theme: readPreference('theme', 'light') === 'dark' ? 'dark' : 'light',
        lang: readPreference('lang', 'pt') === 'en' ? 'en' : 'pt',
        t(pt, en) { return this.lang === 'en' && en ? en : pt; },
        init() {
            document.documentElement.classList.toggle('dark', this.theme === 'dark');
            document.documentElement.lang = this.lang === 'en' ? 'en' : 'pt-BR';
            this.$watch('theme', value => {
                savePreference('theme', value);
                document.documentElement.classList.toggle('dark', value === 'dark');
            });
            this.$watch('lang', value => {
                savePreference('lang', value);
                document.documentElement.lang = value === 'en' ? 'en' : 'pt-BR';
            });
        }
    }));
});
