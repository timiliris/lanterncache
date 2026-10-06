# LanternCache documentation

<img src="https://raw.githubusercontent.com/timiliris/lanterncache/main/assets/lanterncache-icon.png" width="96" height="96" alt="LanternCache icon">

**Préparez vos jeux pendant la nuit, puis servez les fichiers depuis votre réseau local.** LanternCache fournit une interface pour LanCache et SteamPrefill, avec une bibliothèque Steam, des journaux, une planification et une interface français/anglais.

**Prepare games overnight and serve cached downloads on your LAN.** This wiki covers the supplied Linux Docker Compose installation. It is an independent dashboard, not an official Valve product.

## Start here / Pour commencer

| Guide | What you will find |
| --- | --- |
| [Guide en français](Guide-francais) | Installation, DNS, utilisation et dépannage en français. |
| [Installation](Installation) | Requirements, storage, Compose, Steam login and client setup. |
| [Configuration](Configuration) | Environment variables and example network layout. |
| [DNS and local address](DNS-and-local-address) | Client DNS, Tailscale, mDNS and reverse proxy. |
| [Downloads and schedule](Downloads-and-schedule) | Game selection, manual actions, nightly window and limits. |
| [Troubleshooting](Troubleshooting) | Manifest failures, cache misses, Docker and local access. |
| [Operations](Operations) | Updates, backups and stopping the stack. |
| [Security](Security) | Docker socket, private credentials and trusted-network access. |
| [Translations](Translations) | Add a language or improve English/French. |
| [Contributing](Contributing) | Development checks, bug reports and wiki maintenance. |

## Preview

![Steam game library](https://raw.githubusercontent.com/timiliris/lanterncache/main/docs/images/library-en.png)

Screenshots use example network details and demonstration activity.

## Before installing

Opening the dashboard alone does not activate Steam caching: configure client DNS. The first download still uses your Internet connection. Cached content must match the requested version to be reused. SteamPrefill needs an account with access to the selected games.

Keep this administration UI on a trusted LAN or private VPN. It has no built-in user authentication and its Docker socket permits host-level control. Read [Security](Security).

[Source repository](https://github.com/timiliris/lanterncache) · [Installation source](https://github.com/timiliris/lanterncache/blob/main/docs/INSTALL.md) · [MIT license](https://github.com/timiliris/lanterncache/blob/main/LICENSE)
