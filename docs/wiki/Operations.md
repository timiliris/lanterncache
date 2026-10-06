# Operations and maintenance

## Status and controlled shutdown

```sh
docker compose ps
docker compose logs --tail=100 ui
docker compose logs --tail=100 cache dns
```

To pause future starts, turn off nightly preparation in the UI. To stop current work, use Stop and verify no prefill job is active. In Docker mode prefill jobs are standalone managed containers, so stopping the UI container alone does not stop an already running job or enforce its night-window end.

```sh
docker compose stop ui
docker compose up -d ui
```

These commands stop/restart the scheduler. Starting it during an enabled night window can trigger preparation. `docker compose down` removes Compose containers/networks but does not delete bind-mounted data; stop managed prefill first. Do not delete private state to troubleshoot a UI issue.

## Updates

```sh
git pull --ff-only
docker compose config --quiet
docker compose --profile tools pull cache dns prefill
docker compose up -d --build cache dns ui
```

Schedule maintenance while no prefill job is active. Image references in `.env.example` are pinned. Existing `.env` files are not automatically updated: review upstream releases and deliberately change image digests when upgrading dependencies.

## Backups and storage

Securely back up `.env` and `DATA_ROOT` during a quiet period. That directory contains Steam credentials/tokens, selections and download state; keep backups private. Cached game files can generally be downloaded again and are not a backup of purchases or other files.

Ensure a separate cache disk is mounted before stack startup. Compose restart policies do not enforce host mount dependencies. Adjust `CACHE_DISK_SIZE`, `MIN_FREE_DISK` and displayed `CAPACITY_GIB` together when storage changes. This project does not format or partition disks.

## Data layout

| Location | Content |
| --- | --- |
| `CACHE_ROOT/cache` | Cache content. |
| `CACHE_ROOT/logs` | Cache access logs. |
| `DATA_ROOT/prefill` | Private account, selected games and successful depot tracking. |
| `DATA_ROOT/prefill-meta` | Persistent SteamPrefill metadata. |
| `DATA_ROOT/jobs` | Temporary private job configurations, cleaned after processing. |
| `DATA_ROOT/settings.json` | Scheduler toggle and last-start date. |
| `DATA_ROOT/job.json`, `last-job.log` | Recent job status and diagnostic log. |

Do not enable a second systemd scheduler against the same account/cache alongside Docker mode.
