# Access and security model

LanternCache is a trusted-home-network administration tool. It has no built-in account system or per-user authorization. Anyone who can open its UI can obtain the browser action token and start, stop, select, or schedule downloads.

## Docker socket

The Docker-mode UI mounts `/var/run/docker.sock`. This grants Docker Engine control; compromise of the UI can lead to host-level access, including starting containers with host mounts. It is **not** a read-only monitoring dashboard. A read-only bind mount of the socket would not make Docker API requests read-only, either.

The supplied backend limits its own normal actions to labelled prefill jobs and configured container names. These limits reduce accidental interference; they do not make access to the raw Docker socket unprivileged. Run the UI on a host and network you trust.

## Network exposure

Compose defaults the UI publication to loopback when `UI_BIND_IP` is absent. `.env.example` contains a sample LAN address that must be replaced deliberately. Use a trusted LAN address or a private VPN with appropriate access policy. Do not forward port 8088 from your Internet router.

If several people or an untrusted network can reach the host, put authentication at a reverse proxy or access gateway. Restrict the UI's direct port as well so the proxy cannot be bypassed. Allow only intended origins in `ALLOWED_ORIGINS`; scheme, hostname, and port must match the browser's address.

Origin checks, Host validation, and a CSRF token help block hostile websites from making browser actions. They do not authenticate someone who can directly reach the service. `lanterncache.local` and `cacheflow.local` are convenience names, not access controls.

Plain HTTP is intended for the trusted LAN. Use HTTPS at your access gateway if your clients or route cross an untrusted network. Steam credentials are entered through the terminal, not transmitted through browser login forms.

## Private data

`DATA_ROOT` contains Steam account credentials, refreshed tokens, selected games, and download state. Keep this directory outside any SMB share and restrict permissions. Temporary per-job directories are removed after processing; backups of the main account configuration still contain credentials.

Logs may contain game identifiers, remote addresses, or account-related diagnostics. The server filters obvious password/token lines before serving logs, but review every log before publishing it. Never submit `account.config`, `.env`, tokens, or raw state-directory archives to issues.

Container images and external artwork are third-party resources. Review upstream changes before upgrading pinned images. Game content should remain on your own cache disk and must not be committed to this repository.

## Reporting a vulnerability

Use the repository's private vulnerability reporting feature if enabled. Otherwise contact the maintainer privately; do not post working tokens or private host information in a public issue. Include the affected version, attack prerequisites, and reproduction steps using dummy data.
