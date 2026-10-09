# Troubleshooting

Start with the failing layer: UI access, DNS, Steam login, manifests, then game-file transfers.

| Symptom | Checks and next action |
| --- | --- |
| Dashboard does not open | Try the server IP and port; inspect `docker compose ps` and UI logs; verify `UI_BIND_IP`, firewall and mounted storage. |
| Local name fails | Try the IP first; check Avahi publisher, UDP 5353, same LAN and DNS/NRPT policy. See [DNS](DNS-and-local-address). |
| Browser action forbidden | Match the actual scheme, hostname and port in `ALLOWED_ORIGINS`, recreate UI, then reload to refresh its action token. |
| Steam ignores cache | Resolve `lancache.steamcontent.com` from the client; verify it points to `CACHE_IP`; restart Steam and inspect cache requests. |
| Server cannot reach cache IP | Host-to-child isolation is expected with macvlan. Test from a different LAN device; prefill shares the cache namespace. |
| Unable to download manifests / AsyncJobFailedException | Inspect Steam authentication, game access and upstream logs. Reauthenticate during an idle period; run Check Steam before a large prefill. Do not erase working cache content as a first response. |
| Missing SteamPrefill image | Run `docker compose --profile tools pull prefill`. The backend expects the image locally. |
| Download busy | Wait for or stop the current managed job. Only one is supported. |
| Container name collision | Choose a host without conflicting `lanterncache-*` containers or resolve your existing deployment's names. The backend refuses to remove or stop an unmanaged job container. |
| Nightly run absent | Check schedule toggle, local time/window, running UI, credentials, non-empty selections and whether today's session has already started. |
| Preparation recorded but update still needed | This compares local manifests with preparation history; it cannot verify the latest upstream version or retained files. Run manual preparation to check the current depots; confirm HIT requests for matching files. |
| OS disk fills | Verify your cache mount and `CACHE_ROOT`; stop the stack and correct mount ordering before restarting. |

## Collect evidence

```sh
docker compose ps
docker compose logs --tail=100 ui
docker compose logs --tail=100 cache dns
python3 scripts/check-install.py --running
```

For a bug report include Linux/Docker versions, reproduction steps and reviewed, redacted logs. Never attach `.env`, `account.config`, tokens or a raw `DATA_ROOT` archive. Avoid concurrent terminal account changes and UI prefill jobs.

## Selection does not appear

Wait for the next 5-second refresh. Confirm SteamPrefill wrote `DATA_ROOT/prefill/selectedAppsToPrefill.json` in the same state directory used by the UI. Games appear immediately by app ID even if the Steam Store metadata lookup fails. A malformed selection produces unavailable-data feedback rather than an invented library.
