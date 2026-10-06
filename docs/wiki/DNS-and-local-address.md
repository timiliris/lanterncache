# DNS, Tailscale and friendly addresses

The dashboard address and caching DNS address serve different purposes:

| Example | Role |
| --- | --- |
| `192.168.1.10:8088` | UI on the Docker host. |
| `192.168.1.250` | Dedicated cache IP: DNS and cached HTTP downloads. |
| `lanterncache.local` | Optional mDNS alias for the UI host. |

## Client DNS

Follow [Installation](Installation) for the Windows NRPT commands or configure clients/router forwarding to `CACHE_IP`. An unrelated secondary DNS can bypass caching. Restart Steam after DNS changes, verify the resolution of `lancache.steamcontent.com`, and inspect real cache requests. A first request can MISS; only a matching repeated request can HIT.

With Tailscale, inspect effective policy using `Get-DnsClientNrptPolicy`. The scoped Steam rule does not change the dashboard's hostname. `.local` discovery normally remains on the same LAN; it is not automatically carried across a tailnet or VLAN.

## Advertise the UI name

```sh
avahi-publish-address -R lanterncache.local 192.168.1.10
```

Use your UI host IP. `-R` avoids adding a reverse record; the process must remain running. [Installation](Installation) explains the supplied persistent systemd publisher. Allow UDP 5353 on the intended LAN. Add `http://lanterncache.local:8088` to `ALLOWED_ORIGINS` and recreate the UI.

If mDNS fails, try the numeric UI address first. A local DNS record such as `lanterncache.home.arpa`, or a hosts-file entry, is an alternative. On Windows, edit `%SystemRoot%\System32\drivers\etc\hosts` as administrator, preserving existing entries:

```text
192.168.1.10 lanterncache.local
```

Flush the DNS cache and reload the browser. Replace the example IP; remove the entry when your server address changes.

## Without a port

Use an existing reverse proxy on the UI host. A host-native Caddy example:

```caddyfile
http://lanterncache.local {
    reverse_proxy 127.0.0.1:8088
}
```

Set `UI_BIND_IP=127.0.0.1` and allow `http://lanterncache.local`. A container's loopback is its own namespace; adapt the upstream or use a shared network. Port 80 on `CACHE_IP` already belongs to LanCache. Keep the proxy private; see [Security](Security).
