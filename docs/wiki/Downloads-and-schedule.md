# Downloads and nightly preparation

## Controls

| Control | Behaviour |
| --- | --- |
| Prepare now / Check for updates | Immediately prefill the chosen game's current Windows depots, outside or inside the night window. An update check here can download files. |
| Check Steam | Verify login and manifests for selected games with SteamPrefill's `--no-download`; no game chunks are downloaded. |
| Prepare overnight checkbox | Include or exclude a game from nightly preparation. |
| Nightly prefill toggle | Enable or disable future scheduled starts; use Stop for an already running job. |
| Stop | Stop the managed prefill job while retaining cached files. |

Only one managed prefill job runs at a time. Busy controls are disabled; the activity indicator describes work, not an exact percentage.

The status strip shows the current game, why new starts are blocked, and the timestamp of the sampled data. Actions show a persistent response with a link to logs when relevant. While the dashboard stays open, the transition from a running session to idle produces an end-of-session notice; this is not a claim that every game succeeded. Manual refresh reports success only after receiving valid, recent server data. The featured artwork has subtle motion with a pause button and respects the system's reduced-motion preference.

## Night window

Default: **01:00–07:00, Europe/Brussels**. Configure `TZ`, `NIGHT_START` and `NIGHT_END` in `.env`, then recreate the UI with `docker compose up -d ui`. The window must satisfy `0 <= NIGHT_START < NIGHT_END <= 24`; crossing midnight is not supported.

In Docker mode the UI runs the scheduler. It can start once per local calendar date within the window if credentials and game selections exist. Starting the UI during the window can start that day's preparation. There is no catch-up download outside the window. A stopped job does not automatically resume later the same day.

The nightly job first checks manifests in a separate phase. If that check succeeds and the window is still open, game downloads begin. Scheduled jobs are stopped after the window ends; manual jobs are not limited by this schedule. Previously cached files remain.

The schedule is a time window, not an Internet bandwidth limiter. Configure router SQM or a separate bandwidth policy if you need controlled throughput.

## Select more games

```sh
docker compose run --rm prefill select-apps
```

Use a quiet period with no prefill job running. Steam account ownership/access requirements still apply. The library automatically follows the SteamPrefill selection, including additions and removals, every 5 seconds. Steam Store names are fetched asynchronously and cached; unavailable names fall back to the app ID. Deselecting a card removes it from the library; select it again through SteamPrefill.

Preparation recorded means all locally observed latest manifests match SteamPrefill history; Partially prepared means some match; Not verified means there is no successful matching evidence. Counts show prepared versus observed depots, not bytes or a guarantee of the latest patch. During a running job, its log identifies the current game. External terminal sessions block new launches; stop them from their original terminal. Hit ratio is a sample of bytes from successful HTTP responses. Throughput measures completed responses, so large responses can create spikes. Steam downloads may fail before chunks arrive; see [Troubleshooting](Troubleshooting).
