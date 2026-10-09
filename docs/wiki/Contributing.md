# Contributing

Small, focused pull requests are welcome: fixes, translations, installation documentation and UI improvements.

## Development checks

```sh
python -m py_compile server.py runtime.py catalog.py docker_backend.py scripts/check-install.py
python -m unittest discover -s tests -v
python scripts/check-translations.py
node scripts/test-i18n.cjs
node scripts/test-feedback.cjs
node --check app.js
node --check i18n.js
node --check ux.js
docker compose --env-file .env.example config --quiet
docker build -t lanterncache-ui:check .
```

The tests use mocks and temporary state; they do not need a Steam account or running Docker daemon. The Docker build requires Docker. Use a test deployment for real download actions. Verify English/French, keyboard access and narrow screens when changing the interface.

## Documentation and wiki

The main repository stores wiki Markdown in `docs/wiki/` so contributors can propose edits by pull request. Maintainers publish those files to the separate wiki Git repository:

```sh
git clone https://github.com/timiliris/lanterncache.wiki.git
cp docs/wiki/*.md lanterncache.wiki/
cd lanterncache.wiki
git add .
git commit -m "Update wiki documentation"
git push
```

This assumes you run the clone/copy commands from the project root and have wiki write permission. Keep mirrored Installation, Security and Translations pages aligned with their source guides. Review changes before publishing; do not overwrite unrelated wiki contributions silently.

## Reports and translations

Use [Issues](https://github.com/timiliris/lanterncache/issues) for bugs with reproducible steps and redacted logs. See [Translations](Translations) for language contributions. Preserve placeholder names and accessible labels. Never commit credentials, production configuration or downloaded game content.

See [branding notes](https://github.com/timiliris/lanterncache/blob/main/docs/BRANDING.md) for the generated icon and demonstration screenshots; third-party game imagery retains its own rights.
