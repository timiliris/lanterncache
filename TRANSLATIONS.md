# Translate LanternCache

English and French are included. The interface initially follows the browser language (French for `fr-*`, English otherwise). The language picker persists your choice in this browser. Changing language does not interrupt downloads.

## Add a language

1. Copy `locales/en.json` to `locales/<code>.json`, for example `locales/de.json`. Use a short BCP 47 language code.
2. Translate the values, keeping every key. Keep placeholders such as `{host}`, `{value}`, `{start}`, `{end}`, `{zone}` and `{jobs}` exactly as written. Values are plain text; do not add HTML.
3. Add the code to `supported` in `i18n.js`. Add an option to the `#language` selector in `index.html`, using the language's own name.
4. Extend the `locale` getter and browser-language matching in `i18n.js` for localized number formatting and automatic selection. For right-to-left languages, also set the document direction in `apply()` and verify the layout.
5. The server serves locale catalogs matching `locales/<code>.json`; if your checkout uses an explicit asset allowlist, add the file there as well.
6. Run `python scripts/check-translations.py`, then test every view, game cards, dialog, success/error feedback, offline state and mobile layout in the new language. Use a test installation for download controls.
7. Open a pull request with the language code and screenshots. No Steam account, token, private IP address or log export is needed.

## Add or change interface text

Add the same semantic key to every catalog. Static HTML uses `data-i18n="key"`; accessible names use `data-i18n-aria="key"`, and image descriptions use `data-i18n-alt="key"`. JavaScript uses `window.CacheflowI18n.t('key', {placeholder: value})`. The internal helper name is retained for compatibility.

Use complete phrases so translators can change word order. Format numbers with the active locale. Avoid concatenating translated fragments. The English catalog is the fallback for missing keys.

Game names, upstream Steam logs and cache protocol codes (HIT/MISS, Mbit/s) retain their original form. The UI translates its controls and status messages; it does not rewrite upstream diagnostic logs. Unknown custom game genres are supplied by the server.

## Français

Copiez `locales/en.json` vers `locales/<code>.json`, traduisez les valeurs et conservez les clés ainsi que les variables entre accolades. Ajoutez la langue au sélecteur et à `supported` dans `i18n.js`, puis adaptez le format des nombres et la détection de la langue du navigateur. Exécutez le validateur et vérifiez toutes les vues, les retours utilisateur et la version mobile avant de proposer votre contribution.
