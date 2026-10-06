# Configuration reference

Edit `.env` in your project directory, then validate with `docker compose config --quiet`. Recreate affected containers with `docker compose up -d --build cache dns ui`. Replace example addresses and ensure storage is mounted first.

| Setting | Purpose |
| --- | --- |
| `LAN_INTERFACE` | Wired Linux interface; inspect `ip -br address`. |
| `LAN_SUBNET`, `LAN_GATEWAY` | LAN network and router address. |
| `CACHE_IP` | Dedicated unused LAN IP for LanCache and its DNS server. |
| `CACHE_ROOT` | Absolute host directory containing `cache/` and `logs/` on your disk. |
| `DATA_ROOT` | Absolute host directory for dashboard state and private Steam configuration. |
| `UI_BIND_IP` | Server LAN address to publish the dashboard on, separate from `CACHE_IP`. |
| `UI_PORT` | Dashboard port, default `8088`. |
| `ALLOWED_ORIGINS` | Comma-separated browser origins, including scheme and port. No wildcard. |
| `CACHE_DISK_SIZE`, `MIN_FREE_DISK` | Cache limit and free-space reserve; both must fit the disk. |
| `CAPACITY_GIB` | Dashboard display limit, in GiB. |
| `TZ`, `NIGHT_START`, `NIGHT_END` | Nightly preparation timezone and start/end hours. |


## Additional variables

| Variable | Purpose |
| --- | --- |
| `UPSTREAM_DNS` | Resolver used for uncached domains; must be reachable. |
| `HOST_LABEL` | Display name in the UI. |
| `CACHE_INDEX_SIZE` | LanCache in-memory cache index size. |
| `CACHE_MAX_AGE` | Maximum cached-object age. |
| `LANCACHE_IMAGE`, `LANCACHE_DNS_IMAGE`, `PREFILL_IMAGE` | Upstream image references; examples are pinned by digest. |

`ALLOWED_ORIGINS` lists exact browser origins, such as `http://192.168.1.10:8088` or `http://lanterncache.local`. It does not authenticate users. `CAPACITY_GIB` changes the displayed limit, while `CACHE_DISK_SIZE` controls the upstream cache configuration.

Compose sets internal `CACHEFLOW_*` variables for path mapping and the backend. These legacy names remain for compatibility; generally edit the public `.env` settings instead. Keep `DATA_ROOT` absolute because jobs mount it through the host Docker daemon.

See [Security](Security), [Installation](Installation) and [Downloads and schedule](Downloads-and-schedule).
