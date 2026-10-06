#!/usr/bin/env python3
"""Read-only installation checks. Never prints account or .env contents."""
import argparse
import ipaddress
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--running', action='store_true', help='also inspect running Compose services')
args = parser.parse_args()
errors = []

def check(ok, label):
    print(('OK   ' if ok else 'FAIL ') + label)
    if not ok: errors.append(label)

def command(parts):
    result = subprocess.run(parts, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(parts))
    return result.stdout

check(platform.system() == 'Linux', 'Linux host for macvlan networking')
check(shutil.which('docker') is not None, 'Docker CLI installed')
check(Path('.env').is_file(), 'Local .env exists')
if errors:
    sys.exit(1)
try:
    config = json.loads(command(['docker', 'compose', 'config', '--format', 'json']))
    env = config['services']['ui']['environment']
    data = Path(env['CACHEFLOW_HOST_DATA'])
    check(data.is_absolute(), 'DATA_ROOT is an absolute host path')
    check(data.is_dir(), 'DATA_ROOT exists')
    check((data / 'prefill').is_dir(), 'Private prefill directory exists')
    mounts = config['services']['cache']['volumes']
    for volume in mounts:
        source = Path(volume['source'])
        check(source.is_absolute() and source.is_dir(), 'Cache bind directory exists: ' + volume['target'])
    network = config['networks']['lan']
    interface = network['driver_opts']['parent']
    check((Path('/sys/class/net') / interface).exists(), 'Configured LAN interface exists')
    subnet = ipaddress.ip_network(network['ipam']['config'][0]['subnet'])
    cache_ip = ipaddress.ip_address(env['CACHEFLOW_CACHE_IP'])
    check(cache_ip in subnet and cache_ip not in (subnet.network_address, subnet.broadcast_address), 'Cache IP is a usable address in LAN subnet')
    check(bool(env.get('CACHEFLOW_ALLOWED_ORIGINS')), 'Explicit allowed UI origins configured')
    start = int(env['CACHEFLOW_NIGHT_START']); end = int(env['CACHEFLOW_NIGHT_END'])
    check(0 <= start < end <= 24, 'Schedule hours fit one local calendar day')
    if args.running:
        for service in ('cache', 'dns', 'ui'):
            container_id = command(['docker', 'compose', 'ps', '-q', service]).strip()
            check(bool(container_id), service + ' container exists')
            if container_id:
                state = json.loads(command(['docker', 'inspect', container_id]))[0]['State']
                check(state.get('Running', False), service + ' container is running')
        log_mount = next(v for v in mounts if v['target'] == '/data/logs')
        check((Path(log_mount['source']) / 'access.log').exists(), 'Cache access log exists (after requests)')
    print('Manual checks: reserve CACHE_IP outside DHCP; verify client DNS resolves lancache.steamcontent.com to CACHE_IP.')
    print('No downloads, network changes, credential reads, or disk modifications were performed.')
except (KeyError, ValueError, RuntimeError, OSError) as exc:
    check(False, str(exc))
sys.exit(1 if errors else 0)
