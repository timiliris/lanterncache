"""Portable runtime configuration. No site-specific data belongs in the source."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(os.environ.get('CACHEFLOW_BASE', '/data'))
CACHE_ROOT = Path(os.environ.get('CACHEFLOW_CACHE_ROOT', '/cache'))
ACCESS_LOG = Path(os.environ.get('CACHEFLOW_ACCESS_LOG', str(CACHE_ROOT / 'logs/access.log')))
MODE = os.environ.get('CACHEFLOW_MODE', 'docker')
TIMEZONE = os.environ.get('CACHEFLOW_TZ', 'Europe/Brussels')
CACHE_IP = os.environ.get('CACHEFLOW_CACHE_IP', '')
HOST_LABEL = os.environ.get('CACHEFLOW_HOST_LABEL', 'LanternCache')
CAPACITY = int(os.environ.get('CACHEFLOW_CAPACITY_GIB', '1000')) * 1024**3
NIGHT_START = int(os.environ.get('CACHEFLOW_NIGHT_START', '1'))
NIGHT_END = int(os.environ.get('CACHEFLOW_NIGHT_END', '7'))
if not 0 <= NIGHT_START < NIGHT_END <= 24:
    raise ValueError('Night hours must satisfy 0 <= start < end <= 24')
PUBLIC_ORIGINS = {x.strip().rstrip('/') for x in os.environ.get('CACHEFLOW_ALLOWED_ORIGINS', '').split(',') if x.strip()}
ALLOWED_HOSTS = {x.strip().lower() for x in os.environ.get('CACHEFLOW_ALLOWED_HOSTS', 'localhost,127.0.0.1,lanterncache.local,cacheflow.local').split(',') if x.strip()}
ALLOWED_HOSTS.update(urlsplit(origin).hostname for origin in PUBLIC_ORIGINS if urlsplit(origin).hostname)
CONFIG = {
    'sshHost':os.environ.get('CACHEFLOW_SSH_HOST', ''),
    'sshUser':os.environ.get('CACHEFLOW_SSH_USER', 'root'),
    'basePath':os.environ.get('CACHEFLOW_HOST_DATA', str(BASE)),
    'timezone':TIMEZONE, 'nightStart':f'{NIGHT_START:02d}:00', 'nightEnd':f'{NIGHT_END:02d}:00',
    'hostLabel':HOST_LABEL, 'mode':MODE,
    'loginCommand':os.environ.get('CACHEFLOW_LOGIN_COMMAND', 'docker compose run --rm prefill select-apps'),
}

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data), encoding='utf-8')
    tmp.chmod(0o600)
    tmp.replace(path)
