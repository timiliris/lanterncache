# Activity history

Open **Activity & logs** to see the network chart, the 40 latest sampled cache requests, the current download log, and persistent activity history.

The history records UI requests (prepare, verify, stop, schedule, selection) and sessions observed by the server sampler. Filter All, Sessions, Actions or Failures, expand an event for details, and copy a session's log excerpt. The list starts when this feature is installed; older sessions are not reconstructed.

## What the results mean

- **Request accepted**: the server accepted the operation, not proof that a download completed.
- **Running**: the sampler observed an active session.
- **Session ended**: the session is no longer active. Check its excerpt for individual game results; this does not certify success or current cached content.
- **Failed**: a request failed, the managed Docker backend reported failure, or a terminal failure was observed in the session log. Errors outside the observed excerpt may still require inspection of the server logs.

Times are observation times. Short sessions that start and finish between sampler polls may have an action record without a session record. Games are listed when the sampler can identify them. External terminal sessions retain the last observed excerpt; unrelated old service logs are not assigned to them.

## Storage and limits

History is stored privately at `DATA_ROOT/ui-activity.json`, survives UI restarts, and is bounded to the **200 most recent events**. Each log excerpt is limited to the last 120 observed lines and 12,000 characters. Lists omit log bodies; details load separately. Progress charts and sampled request rows are live samples, not a persistent archive of every network request.

Credential-related log lines are removed, and request headers, passwords and arbitrary request fields are never recorded. Treat this file as private operational data; it is excluded from Git and Docker build context. Access follows the same private-network policy as the dashboard. Back it up with your private state directory if needed.

## En français

La vue **Activité & journaux** garde les 200 derniers événements sur le serveur. Les filtres distinguent sessions, actions et échecs. Dépliez une entrée pour consulter les horaires observés et copier son extrait de journal. Les données survivent à un redémarrage de l’interface.

L’historique commence à l’installation de cette fonctionnalité. « Demande acceptée » ne signifie pas que le téléchargement est terminé, et « Session terminée » ne garantit pas la réussite de tous les jeux. Les sessions très courtes peuvent échapper à l’échantillonnage ; leur demande reste enregistrée si elles viennent de l’interface.
