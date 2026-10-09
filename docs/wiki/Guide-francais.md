# Installer et utiliser LanternCache

## Le fonctionnement

LanCache conserve les fichiers de téléchargement compatibles. SteamPrefill prépare ceux de vos jeux avant de les installer sur le PC. LanternCache affiche le cache et pilote cette préparation. Le premier transfert utilise Internet ; une demande identique peut ensuite être servie sur le réseau local.

## Préparer le serveur

Il faut un serveur Linux avec Docker Engine et le plugin Compose, une interface Ethernet, un disque déjà monté et une adresse IPv4 disponible pour le cache. L'installation ne formate aucun disque. Vérifiez que le disque est monté avant le démarrage des conteneurs.

Deux adresses ont des rôles différents : `192.168.1.10` représente le serveur de l'interface, et `192.168.1.250` le cache et son DNS. Ce sont des exemples à remplacer. Réservez l'adresse du cache ou excluez-la de la plage DHCP.

```sh
git clone https://github.com/timiliris/lanterncache.git
cd lanterncache
cp .env.example .env
```

Modifiez `.env` : interface Linux, sous-réseau, passerelle, adresses, chemins absolus, taille du cache, fuseau et origines autorisées. Les chemins par défaut sont `/srv/lancache` pour le cache et `/srv/lanterncache` pour les données privées. Consultez [Configuration](Configuration) pour chaque variable.

```sh
sudo mkdir -p /srv/lancache/cache /srv/lancache/logs /srv/lanterncache/prefill
sudo chmod 700 /srv/lanterncache /srv/lanterncache/prefill
python3 scripts/check-install.py
docker compose config --quiet
docker compose --profile tools pull cache dns prefill
docker compose up -d --build cache dns ui
docker compose run --rm prefill select-apps
```

Connectez-vous à Steam et validez Steam Guard dans le terminal. Sélectionnez les jeux auxquels le compte a accès. Le navigateur ne demande pas votre mot de passe Steam. Ne publiez jamais `account.config` ni `.env`.

Ouvrez `http://192.168.1.10:8088` avec l'adresse réelle du serveur. La planification est activée au départ ; si vous vous connectez pendant le créneau nocturne, une préparation peut commencer. Désactivez-la dans l'interface avant la connexion Steam si vous souhaitez différer ce lancement.

## Activer le cache sur Windows

Dans PowerShell administrateur, cette règle cible uniquement le domaine de découverte du cache Steam :

```powershell
Add-DnsClientNrptRule -Namespace 'lancache.steamcontent.com' -NameServers '192.168.1.250' -Comment 'LanternCache Steam cache'
Clear-DnsClientCache
Resolve-DnsName lancache.steamcontent.com -Type A
```

Remplacez l'adresse par celle du cache. Le résultat doit pointer vers cette adresse. Redémarrez Steam et vérifiez les requêtes dans l'interface. Avec Tailscale, vérifiez les règles NRPT effectives : une règle générale peut modifier la résolution. Voir [DNS et adresse locale](DNS-and-local-address).

## Préparer les jeux

Les cases de la bibliothèque choisissent les jeux nocturnes. « Préparer maintenant » et « Vérifier les mises à jour » lancent un remplissage manuel immédiatement, y compris hors du créneau. « Tester Steam » vérifie la connexion et les manifestes des jeux sélectionnés sans télécharger les fichiers de jeu.

La plage par défaut est **01:00–07:00 Europe/Brussels**. Le fuseau et les heures se configurent dans `.env`, puis en recréant l'interface. Le bouton de planification active ou désactive les prochaines sessions ; pour interrompre une session déjà lancée, utilisez « Arrêter ». Les fichiers en cache restent disponibles.

La bibliothèque suit automatiquement la sélection SteamPrefill toutes les 5 secondes, ajouts et retraits compris. Les noms arrivent depuis Steam et sont mémorisés ; les jaquettes utilisent l’identifiant du jeu. Décocher un jeu le retire de la sélection et de la bibliothèque : sélectionnez-le à nouveau dans SteamPrefill pour le retrouver. « Préparation enregistrée » signifie que les manifestes locaux observés correspondent à l’historique, « partielle » que certains correspondent et « non vérifié » que les preuves manquent. Le compteur concerne les manifestes, pas le volume réel en cache ni une garantie de la dernière version. Une session lancée dans un terminal apparaît comme active ; arrêtez-la depuis ce terminal.

## Adresse simple et dépannage

Pour `lanterncache.local`, utilisez Avahi sur le serveur et autorisez mDNS sur le LAN. Une entrée DNS locale `lanterncache.home.arpa` ou une entrée du fichier hosts constitue une alternative. Un reverse proxy permet d'enlever le port `:8088`. Le nom de l'interface pointe vers le serveur, pas vers l'adresse dédiée du cache.

Si le nom échoue, essayez directement l'adresse IP. Si Steam ignore le cache, vérifiez le DNS et redémarrez Steam. Une erreur de manifeste peut venir de l'authentification ou des droits du compte avant tout transfert : ne supprimez pas le cache pour commencer. Le réseau macvlan peut empêcher le serveur de joindre sa propre adresse de cache ; testez depuis un autre appareil du LAN.

Voir [Dépannage](Troubleshooting), [Exploitation](Operations), [Sécurité](Security) et [Traductions](Translations).
