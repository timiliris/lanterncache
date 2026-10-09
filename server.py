#!/usr/bin/env python3
import collections
import datetime as dt
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from runtime import BASE, CACHE_ROOT, ACCESS_LOG, MODE, TIMEZONE, CACHE_IP, HOST_LABEL, CAPACITY, CONFIG, PUBLIC_ORIGINS, ALLOWED_HOSTS
from docker_backend import Backend
from catalog import Catalog, selection
from activity import Activity

ROOT = Path(__file__).parent
TOKEN = secrets.token_hex(32)
LOCK = threading.Lock()
ACTION_LOCK = threading.Lock()
STATE = {}
PORT = int(os.environ.get('PORT', '8088'))
BIND = os.environ.get('BIND', '127.0.0.1')
BACKEND = Backend() if MODE=='docker' else None
CATALOG = Catalog()
ACTIVITY = Activity()

def run(*args, timeout=8):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ''

def read_json(path, default):
    try: return json.loads(path.read_text())
    except (OSError, ValueError): return default

def tail(path, limit=200000):
    try:
        with path.open('rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell()-limit))
            return f.read().decode('utf-8', 'replace')
    except OSError: return ''

ACCESS = re.compile(r'^\[([^]]+)\].*?\[([^]]+)\] "(?:GET|HEAD) ([^ ]+) HTTP/[^" ]+" (\d+) (\d+) "[^"]*" "[^"]*" "([^"]*)"')

def sampler():
    global STATE
    history = collections.deque(maxlen=180)
    last_sample = None
    offset = 0
    disk_bytes = 0
    du_at = 0
    log_container = None
    current_start = None
    while True:
        started = time.monotonic()
        try:
            now = dt.datetime.now(ZoneInfo(TIMEZONE))
            log = ACCESS_LOG
            recent = []
            for line in tail(log).splitlines():
                m = ACCESS.match(line)
                if m and int(m[4]) == 200 and int(m[5]) > 0:
                    recent.append({'service':m[1], 'time':m[2], 'path':m[3], 'status':int(m[4]), 'bytes':int(m[5]), 'cache':m[6]})
            hits = sum(r['bytes'] for r in recent if r['cache']=='HIT')
            misses = sum(r['bytes'] for r in recent if r['cache']!='HIT')
            new_bytes = 0
            try:
                with log.open('rb') as f:
                    f.seek(0,2); end = f.tell()
                    if offset and end >= offset:
                        f.seek(max(offset, end-2000000))
                        for line in f.read().decode('utf-8','replace').splitlines():
                            m = ACCESS.match(line)
                            if m and int(m[4]) == 200 and int(m[5]) > 0: new_bytes += int(m[5])
                    offset=end
            except OSError: pass
            sampled=time.monotonic()
            elapsed=sampled-last_sample if last_sample is not None else 5
            last_sample=sampled
            history.append({'time':now.strftime('%H:%M:%S'), 'timestamp':now.isoformat(), 'mbps':round(new_bytes*8/max(.001,elapsed)/1e6,2)})
            if time.monotonic()-du_at > 60:
                value = run('du','-s','-B1',str(CACHE_ROOT/'cache'),timeout=20).split()
                if value: disk_bytes=int(value[0])
                du_at=time.monotonic()
            usage = shutil.disk_usage(CACHE_ROOT)
            services = run('systemctl','show','lancache.service','lancache-prefill.timer','lancache-prefill.service','lancache-web-prefill.service','-p','Id','-p','ActiveState','-p','UnitFileState','-p','Result')
            units = {}
            for block in services.split('\n\n'):
                info=dict(x.split('=',1) for x in block.splitlines() if '=' in x)
                if 'Id' in info: units[info['Id']]=info
            containers = run('docker','ps','--format','{{.Names}}').splitlines()
            active=[c for c in containers if 'prefill' in c]
            if not active and units.get('lancache-web-prefill.service',{}).get('ActiveState') in ('active','activating'):
                active=['lancache-web-prefill']
            journal = run('journalctl','-u','lancache-web-prefill.service','-u','lancache-prefill.service','-n','70','--no-pager','-o','cat')
            if active and active[0] in containers:
                job=active[0]
                job_logs=run('docker','logs',*(['--tail','1000'] if job==log_container else []),job)
                if job != log_container: current_start=None
                starts=re.findall(r'(?:^|\n)([^\n]*Starting [^\n]+)',job_logs)
                if starts: current_start=starts[-1]
                log_container=job
                journal=((current_start+'\n') if current_start else '')+'\n'.join(job_logs.splitlines()[-100:]) if job_logs else journal
            journal = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',journal)
            lines = journal.splitlines()
            starts = [i for i,line in enumerate(lines) if line.startswith('Started ')]
            if starts: journal = '\n'.join(lines[starts[-1]:])
            # Never expose authentication tokens, even if an upstream tool logs one.
            journal = '\n'.join(x for x in journal.splitlines() if not re.search(r'token|password|refresh_token|access_token',x,re.I))
            next_time=run('systemctl','show','lancache-prefill.timer','-p','NextElapseUSecRealtime','--value')
            runtime_state={'online':units.get('lancache.service',{}).get('ActiveState')=='active' and 'steamcache-dns-1' in containers,
                           'nightEnabled':units.get('lancache-prefill.timer',{}).get('ActiveState')=='active',
                           'nextRun':next_time,'active':active,'logs':journal,
                           'jobMode':'check' if active and '--no-download' in run('docker','inspect',active[0],'--format','{{json .Config.Cmd}}') else 'download',
                           'canStop':bool(any(units.get(unit,{}).get('ActiveState') in ('active','activating') for unit in ['lancache-web-prefill.service','lancache-prefill.service']) or 'steam-prefill-satisfactory' in active)}
            if BACKEND:
                runtime_state=BACKEND.snapshot(now)
                runtime_state['logs']=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',runtime_state['logs'])
                runtime_state['logs']='\n'.join(line for line in runtime_state['logs'].splitlines() if not re.search(r'token|password|refresh_token|access_token',line,re.I))
            games=CATALOG.games(active=bool(runtime_state['active']),checking=runtime_state['jobMode']=='check',logs=runtime_state['logs'])
            data={'timestamp':now.isoformat(),'cacheBytes':disk_bytes,'capacity':CAPACITY,
                  'disk':{'total':usage.total,'used':usage.used,'free':usage.free},
                  **runtime_state,'games':games,
                  'hitBytes':hits,'missBytes':misses,'sampleRequests':len(recent),
                  'recent':recent[-40:][::-1], 'history':list(history),'speed':history[-1]['mbps'],
                  'cacheIp':CACHE_IP,'host':HOST_LABEL,'config':CONFIG,'csrf':TOKEN}
            ACTIVITY.observe(data)
            with LOCK: STATE=data
        except Exception as exc:
            with LOCK: STATE=dict(STATE,error=str(exc))
        time.sleep(max(0.2,5-(time.monotonic()-started)))

class Handler(BaseHTTPRequestHandler):
    def valid_host(self):
        try:
            name=urlsplit('//'+self.headers.get('Host','')).hostname
            return name is not None and name.lower() in ALLOWED_HOSTS
        except ValueError: return False
    def send(self, code, data, kind='application/json; charset=utf-8'):
        if getattr(self,'audit_action',False):
            try: ACTIVITY.action(self.path,code,self.audit_data)
            except OSError: pass
        body=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,dict) else data
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' https://shared.fastly.steamstatic.com; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host(): return self.send(403,{'error':'Host not allowed','code':'host_forbidden'})
        if self.path=='/api/state':
            with LOCK: data=dict(STATE)
            return self.send(200,data)
        if self.path=='/api/activity': return self.send(200,{'events':ACTIVITY.list(),'limit':200})
        if re.fullmatch(r'/api/activity/[a-f0-9]{32}',self.path):
            item=ACTIVITY.detail(self.path.rsplit('/',1)[1])
            return self.send(200,{'event':item}) if item else self.send(404,{'error':'Unknown event'})
        assets={'/':'index.html','/app.js':'app.js','/chart.js':'chart.js','/style.css':'style.css','/i18n.js':'i18n.js','/ux.js':'ux.js','/assets/lanterncache-icon.png':'assets/lanterncache-icon.png'}
        # Translation filenames are enumerated, never arbitrary filesystem paths.
        for catalog in (ROOT/'locales').glob('*.json'):
            if re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?',catalog.stem): assets['/locales/'+catalog.name]='locales/'+catalog.name
        if self.path not in assets: return self.send(404,{'error':'Page introuvable'})
        name=assets[self.path]
        kind={'html':'text/html','js':'text/javascript','css':'text/css','json':'application/json','png':'image/png'}[name.rsplit('.',1)[1]]
        self.send(200,(ROOT/name).read_bytes(),kind if kind=='image/png' else kind+'; charset=utf-8')

    def do_POST(self):
        with ACTION_LOCK:
            self.handle_action()

    def handle_action(self):
        if not self.valid_host(): return self.send(403,{'error':'Host not allowed','code':'host_forbidden'})
        if not hmac.compare_digest(self.headers.get('X-Cache-Token',''),TOKEN):
            return self.send(403,{'error':'Recharge la page avant de continuer.'})
        expected_origins=PUBLIC_ORIGINS or {'http://'+self.headers.get('Host','')}
        if self.headers.get('Origin') not in expected_origins:
            return self.send(403,{'error':'Origine non autorisee'})
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<=length<=4096: raise ValueError('Requete trop longue')
            data=json.loads(self.rfile.read(length) or '{}')
            if not isinstance(data,dict): raise ValueError('Invalid request')
            if self.path in ('/api/start','/api/check','/api/stop','/api/schedule','/api/selection'):
                self.audit_action=True;self.audit_data=data
            if self.path in ('/api/start','/api/check'):
                selected=selection(BASE)
                if not selected: raise ValueError('selection_empty')
                app=int(data.get('id',selected[0] if self.path=='/api/check' else 0))
                if app not in selected: raise ValueError('Jeu inconnu')
                with LOCK: busy=STATE.get('active',[])
                if busy: return self.send(409,{'error':'Un telechargement est deja en cours.'})
                if BACKEND:
                    BACKEND.start(app,check=self.path=='/api/check')
                    return self.send(200,{'message':'Verification Steam lancee, sans telecharger les jeux.' if self.path=='/api/check' else 'Preparation lancee. Le journal va apparaitre.'})
                if subprocess.run(['flock','-n',str(BASE/'prefill.lock'),'true']).returncode:
                    return self.send(409,{'error':'Un remplissage du cache est deja en cours.'})
                if run('systemctl','is-active','lancache-web-prefill.service') in ('active','activating'):
                    return self.send(409,{'error':'Un lancement est deja en cours.'})
                (BASE/'ui-game-id').write_text(str(app))
                (BASE/'ui-mode').write_text('check' if self.path=='/api/check' else 'download')
                subprocess.run(['systemctl','start','--no-block','lancache-web-prefill.service'],check=True)
                return self.send(200,{'message':'Verification Steam lancee, sans telecharger les jeux.' if self.path=='/api/check' else 'Preparation lancee. Le journal va apparaitre.'})
            if self.path=='/api/stop':
                if BACKEND:
                    BACKEND.stop()
                    return self.send(200,{'message':'Remplissage arrete. Les fichiers deja caches sont conserves.'})
                subprocess.run(['systemctl','stop','lancache-web-prefill.service','lancache-prefill.service'],check=True,timeout=40)
                names=run('docker','ps','--format','{{.Names}}').splitlines()
                for name in names:
                    if name=='steam-prefill-satisfactory': run('docker','stop','-t','10',name,timeout=15)
                return self.send(200,{'message':'Remplissage arrete. Les fichiers deja caches sont conserves.'})
            if self.path=='/api/schedule':
                enabled=data.get('enabled')
                if not isinstance(enabled,bool): raise ValueError('Valeur invalide')
                if BACKEND:
                    BACKEND.schedule(enabled)
                    return self.send(200,{'message':'Preparation nocturne '+('activee.' if enabled else 'en pause.')})
                subprocess.run(['systemctl','enable' if enabled else 'disable','--now','lancache-prefill.timer'],check=True)
                return self.send(200,{'message':'Preparation nocturne '+('activee.' if enabled else 'en pause.')})
            if self.path=='/api/selection':
                app=int(data.get('id',0)); enabled=data.get('enabled')
                if app not in selection(BASE) or not isinstance(enabled,bool): raise ValueError('Selection invalide')
                path=BASE/'prefill/selectedAppsToPrefill.json'
                current=read_json(path,[])
                current=list(dict.fromkeys(current+[app])) if enabled else [x for x in current if x!=app]
                tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(current)); tmp.chmod(0o600); tmp.replace(path)
                return self.send(200,{'message':'Selection nocturne mise a jour.'})
            return self.send(404,{'error':'Commande inconnue'})
        except Exception as exc:
            known={'steam_login_required','selection_empty','download_busy','host_data_required'}
            code=str(exc) if str(exc) in known else 'runtime_error'
            return self.send(409 if code=='download_busy' else 400,{'error':str(exc),'code':code})

if __name__=='__main__':
    threading.Thread(target=sampler,daemon=True).start()
    addresses=os.environ.get('CACHEFLOW_BIND_ADDRESSES',BIND).split(',')
    servers=[ThreadingHTTPServer((address.strip(),PORT),Handler) for address in addresses]
    for server in servers[:-1]: threading.Thread(target=server.serve_forever,daemon=True).start()
    servers[-1].serve_forever()
