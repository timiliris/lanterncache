window.CacheflowI18n = (() => {
  const supported = ['fr', 'en'];
  let language = 'en', catalogs = {};
  const t = (key, variables = {}) => {
    const value = catalogs[language]?.[key] ?? catalogs.en?.[key] ?? key;
    return String(value).replace(/\{(\w+)\}/g, (_, name) => String(variables[name] ?? `{${name}}`));
  };
  function apply() {
    document.documentElement.lang = language;
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label', t(el.dataset.i18nAria)));
    document.querySelectorAll('[data-i18n-alt]').forEach(el => el.alt = t(el.dataset.i18nAlt));
    const selector = document.querySelector('#language');
    if (selector) selector.value = language;
    document.dispatchEvent(new CustomEvent('cacheflow:language'));
  }
  async function init() {
    catalogs = Object.fromEntries(await Promise.all(supported.map(async lang => {
      const response = await fetch(`/locales/${lang}.json`);
      if (!response.ok) throw new Error(`Translation unavailable: ${lang}`);
      return [lang, await response.json()];
    })));
    let preferred;
    try { preferred = localStorage.getItem('lanterncache.language') || localStorage.getItem('cacheflow.language'); } catch {}
    language = supported.includes(preferred) ? preferred : ((navigator.language || '').startsWith('fr') ? 'fr' : 'en');
    document.querySelector('#language')?.addEventListener('change', event => {
      if (!supported.includes(event.target.value)) return;
      language = event.target.value;
      try { localStorage.setItem('lanterncache.language', language); } catch {}
      apply();
    });
    apply();
  }
  return { init, t, get language() { return language; }, get locale() { return language === 'fr' ? 'fr-FR' : 'en-US'; } };
})();
