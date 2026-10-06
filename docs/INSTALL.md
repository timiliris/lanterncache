# Install LanternCache at home

## 1. Requirements

- A Linux server with Docker Engine and the Docker Compose plugin.
- A wired LAN interface and an unused fixed IPv4 address in that LAN, outside its DHCP pool or reserved for the cache.
- A mounted disk with enough free storage for your games.
- A Steam account with the appropriate game licenses.

The supplied stack uses a dedicated macvlan IP for HTTP caching and DNS, avoiding the server's existing web ports. Your network must allow multiple MAC addresses on the server's interface. Some Wi-Fi adapters and virtual-machine networks do not support this setup.

## 2. Configure storage and networking

Clone the repository and copy `.env.example` to `.env`. Replace the example values; they are not automatic network detection.

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

For example, a server at `192.168.1.10` and a cache at `192.168.1.250` have separate addresses. The dashboard is `http://192.168.1.10:8088`; client cache DNS is `192.168.1.250`.

Create your configured directories before starting:

```sh
sudo mkdir -p /srv/lancache/cache /srv/lancache/logs /srv/lanterncache/prefill
sudo chmod 700 /srv/lanterncache /srv/lanterncache/prefill
```

Use your chosen paths rather than copying these examples blindly. The Docker backend uses `CACHEFLOW_HOST_DATA` to create temporary SteamPrefill mounts; Compose sets this to the same absolute host path as `DATA_ROOT`.

If your cache disk is a separate mount, ensure it is mounted before Docker starts this stack. `restart: unless-stopped` does not enforce host mount ordering. An absent mount can otherwise fill the operating-system disk. Use your host's mount/service dependencies when appropriate. This installation does not format or partition disks.

## 3. Start the stack and authenticate Steam

```sh
docker compose config --quiet
docker compose --profile tools pull cache dns prefill
docker compose up -d --build cache dns ui
docker compose ps
docker compose run --rm prefill select-apps
```

Authenticate in the terminal, complete Steam Guard, and choose your games. `account.config` is private: do not share or commit it. Open the dashboard on your server's LAN address and UI port. Manifest checks do not download game files; a manual download starts immediately rather than waiting for the nightly window.

The explicit pull includes SteamPrefill's optional `tools` profile. The UI creates jobs from that local image and does not automatically pull a missing image.

The Docker backend manages its own schedule while the UI container runs. The systemd integration is an alternative mode for administrators extending an existing installation; do not enable two schedulers for the same account/cache.

The initial Docker schedule is enabled and uses 01:00–07:00 in the configured timezone. A start or restart during that window can begin preparation. Disable the schedule in the UI before logging in if you want to avoid that initial run. Set `0 <= NIGHT_START < NIGHT_END <= 24`; the current implementation supports a window within one local calendar day, not a window crossing midnight.

Before installation, run `python3 scripts/check-install.py` from the project directory. It checks configuration, required paths, the host interface, and cache-IP/subnet consistency without changing networking, downloading games, or formatting disks. After starting the stack, add `--running` to check the Docker service state and available logs.

## 4. Activate Steam caching on clients

The [LanCache documentation](https://lancache.net/docs/installation/docker-compose/) describes client DNS configuration. Use `CACHE_IP` as DNS for the intended clients, or have an existing resolver forward only cache domains to it. An unrelated secondary DNS resolver may bypass the cache.

For Steam-only forwarding on Windows, an administrator can use a scoped NRPT rule:

```powershell
Add-DnsClientNrptRule -Namespace 'lancache.steamcontent.com' -NameServers '192.168.1.250' -Comment 'LanternCache Steam cache'
Clear-DnsClientCache
Resolve-DnsName lancache.steamcontent.com -Type A
```

Replace the IP with your `CACHE_IP`; the result should point to that IP. This exact-domain rule can coexist with Tailscale DNS, but verify the effective rules on your PC. To remove just this example rule:

```powershell
Get-DnsClientNrptRule | Where-Object Comment -eq 'LanternCache Steam cache' | Remove-DnsClientNrptRule -Force
Clear-DnsClientCache
```

Restart Steam after DNS changes. Opening the dashboard does not verify game caching: start a small compatible download and inspect the logs. A first request is expected to MISS; a repeated identical request may HIT.

## 5. A friendly local address

`lanterncache.local` uses multicast DNS (mDNS), not ordinary router DNS. The Linux host must advertise that name on the LAN. Changing the host's main hostname affects other services; a separate Avahi alias is usually preferable.

Install Avahi using your distribution package manager, then test a publisher on the host:

```sh
avahi-publish-address -R lanterncache.local 192.168.1.10
```

Use the **server UI address**, not the dedicated cache IP. This foreground command lasts only while it runs. For persistence, copy [`lanterncache-mdns.service`](lanterncache-mdns.service) to `/etc/systemd/system/`, replace the example IP in `ExecStart`, and run:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now lanterncache-mdns.service
```

Check the publisher path with `command -v avahi-publish-address`. Allow mDNS UDP 5353 on the trusted LAN if necessary. Add `http://lanterncache.local:8088` to `ALLOWED_ORIGINS`, recreate the UI container, and open that address. You can advertise `cacheflow.local` as an additional legacy alias if desired.

mDNS normally stays within one local network and does not automatically work over Tailscale or across VLANs. Some Windows installations need mDNS support enabled. If unavailable, use a local router DNS record such as **`lanterncache.home.arpa`**, or the server IP. `home.arpa` is intended for home network names. A per-client hosts-file entry is another option: `192.168.1.10 lanterncache.local`.

For `http://lanterncache.local` without a port, configure your existing reverse proxy to forward that hostname to the UI and add the matching origin. The proxy must run on the UI server address: port 80 on `CACHE_IP` belongs to LanCache.

For a Caddy instance on the same host, this optional Caddyfile entry forwards plain HTTP to a UI published on host loopback port 8088:

```caddyfile
http://lanterncache.local {
    reverse_proxy 127.0.0.1:8088
}
```

Set `UI_BIND_IP=127.0.0.1` and include `http://lanterncache.local` in `ALLOWED_ORIGINS`. Recreate UI and reload Caddy. A Caddy container has its own loopback address: use a shared Docker network or an appropriate host address instead. Keep this route private to the LAN. The same approach works with the optional `cacheflow.local` alias when it is advertised and explicitly allowed.

## 6. Operations

```sh
docker compose logs --tail=100 ui
docker compose logs --tail=100 cache dns
docker compose stop ui                 # also pauses its Docker-mode scheduler
docker compose up -d ui
```

Back up `DATA_ROOT` securely and `.env` privately. Cache content can usually be repopulated; account configuration must not be shared. A cache is not a backup of purchased games or other files.

Images in `.env.example` are pinned for reproducibility. To upgrade, review upstream releases, change the relevant image reference, then run `docker compose pull` and `docker compose up -d --build`.

## Troubleshooting

- **Steam ignores the cache:** verify the client's DNS response, restart Steam, and check whether requests reach `CACHE_IP`.
- **The host cannot reach the dedicated cache IP:** Linux macvlan isolates the host from its own macvlan children by default. Prefill shares the cache network namespace and can reach local DNS. Test connectivity from another LAN device or configure a host macvlan interface separately.
- **Manifest errors:** authentication/session or access problems can happen before game files are fetched. Recheck authentication and logs; do not clear working cache content as a first step.
- **Forbidden browser action:** add the actual scheme, hostname, and port to `ALLOWED_ORIGINS`, recreate UI, and reload the page.
- **Local name fails:** check Avahi, same-LAN connectivity, and mDNS support. Use the IP to distinguish DNS failure from dashboard availability.

## References

- [LanCache environment variables](https://lancache.net/docs/containers/monolithic/variables/)
- [SteamPrefill](https://github.com/tpill90/steam-lancache-prefill)
- [Docker macvlan networking](https://docs.docker.com/engine/network/drivers/macvlan/)
- [Avahi address publication](https://manpages.debian.org/bookworm/avahi-utils/avahi-publish-address.1.en.html)
