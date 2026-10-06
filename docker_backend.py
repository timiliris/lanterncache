"""Docker Engine API adapter. The socket grants host-level access; keep UI private."""
import datetime as dt
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import threading
import urllib.parse

from runtime import BASE, TIMEZONE, NIGHT_START, NIGHT_END, atomic_json

CACHE_CONTAINER=os.environ.get('CACHEFLOW_CACHE_CONTAINER','lanterncache-cache')
DNS_CONTAINER=os.environ.get('CACHEFLOW_DNS_CONTAINER','lanterncache-dns')
JOB_CONTAINER=os.environ.get('CACHEFLOW_JOB_CONTAINER','lanterncache-prefill')
HOST_DATA=os.environ.get('CACHEFLOW_HOST_DATA','')
PREFILL_IMAGE=os.environ.get('CACHEFLOW_PREFILL_IMAGE','tpill90/steam-lancache-prefill@sha256:4c940d040ef422abec322a7b5afabe4adcf052f62d39eca5c2d336ffab0eaccc')
API_VERSION=None

class DockerError(RuntimeError): pass

class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(os.environ.get('DOCKER_SOCKET','/var/run/docker.sock'))

def api(method, path, body=None, raw=False, allow_missing=False):
    global API_VERSION
    connection=UnixConnection('localhost', timeout=15)
    try:
        if API_VERSION is None:
            connection.request('GET','/version')
            version_response=connection.getresponse()
            API_VERSION=json.loads(version_response.read())['ApiVersion']
        connection.request(method, '/v'+API_VERSION+path,
                           body=json.dumps(body).encode() if body is not None else None,
                           headers={'Content-Type':'application/json'})
        response=connection.getresponse(); content=response.read()
        if allow_missing and response.status==404: return None
        if not 200<=response.status<300:
            raise DockerError(f'Docker request failed ({response.status}): {content.decode("utf8","replace")[:200]}')
        if raw: return content
        return json.loads(content) if content else {}
    finally: connection.close()

def inspect(name): return api('GET','/containers/'+urllib.parse.quote(name,safe='')+'/json',allow_missing=True)

def log_text(name):
    content=api('GET',f'/containers/{urllib.parse.quote(name,safe="")}/logs?stdout=1&stderr=1&tail=100',raw=True,allow_missing=True)
    if content is None: return ''
    # Docker's non-TTY log protocol prefixes each frame with an 8-byte header.
    parts=[]; offset=0
    while offset+8<=len(content) and content[offset] in (0,1,2) and content[offset+1:offset+4]==b'\0\0\0':
        length=int.from_bytes(content[offset+4:offset+8],'big')
        parts.append(content[offset+8:offset+8+length]); offset+=8+length
    return b''.join(parts).decode('utf8','replace') if parts else content.decode('utf8','replace')

def load(path, default):
    try: return json.loads(path.read_text())
    except (OSError,ValueError): return default

class Backend:
    def __init__(self):
        self.lock=threading.RLock()
        BASE.mkdir(parents=True,exist_ok=True)
        (BASE/'prefill').mkdir(mode=0o700,exist_ok=True)
        (BASE/'prefill-meta').mkdir(mode=0o700,exist_ok=True)
        self.marker=BASE/'job.json'
        self.settings=BASE/'settings.json'

    def in_window(self, now): return NIGHT_START<=now.hour<NIGHT_END

    def schedule(self, enabled):
        with self.lock:
            settings=load(self.settings,{'nightEnabled':True})
            settings['nightEnabled']=enabled
            atomic_json(self.settings,settings)

    def _container(self, directory, check):
        previous=inspect(JOB_CONTAINER)
        if previous:
            if previous.get('Config',{}).get('Labels',{}).get('io.lanterncache.managed')!='true':
                raise DockerError('Job container name is already used by another application')
            if previous['State']['Running']: raise ValueError('download_busy')
            api('DELETE',f'/containers/{JOB_CONTAINER}')
        host_path=Path(HOST_DATA)/directory.relative_to(BASE)
        args=['prefill','--os','windows','--no-ansi']
        if check: args+=['--no-download','--verbose']
        created=api('POST','/containers/create?name='+JOB_CONTAINER,{
            'Image':PREFILL_IMAGE, 'Cmd':args, 'Env':['TZ='+TIMEZONE],
            'Labels':{'io.lanterncache.managed':'true'},
            'HostConfig':{'NetworkMode':'container:'+CACHE_CONTAINER,
                          'Binds':[str(host_path)+':/Config',str(Path(HOST_DATA)/'prefill-meta')+':/root/.cache/SteamPrefill'],
                          'RestartPolicy':{'Name':'no'}},
        })
        api('POST','/containers/'+created['Id']+'/start')

    def start(self, app, check=False, night=False):
        with self.lock:
            if not HOST_DATA or not Path(HOST_DATA).is_absolute(): raise ValueError('host_data_required')
            current=inspect(JOB_CONTAINER)
            if current and current['State']['Running']: raise ValueError('download_busy')
            account=BASE/'prefill/account.config'
            if not account.exists(): raise ValueError('steam_login_required')
            # Finish an earlier completed job before making a new isolated configuration.
            self._finish(current)
            directory=BASE/'jobs'/dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            directory.mkdir(parents=True,mode=0o700)
            shutil.copy2(account,directory/'account.config')
            completed=BASE/'prefill/successfullyDownloadedDepots.json'
            if completed.exists(): shutil.copy2(completed,directory/completed.name)
            selected=load(BASE/'prefill/selectedAppsToPrefill.json',[])
            apps=selected if check or night else [app]
            if not apps:
                shutil.rmtree(directory); raise ValueError('selection_empty')
            atomic_json(directory/'selectedAppsToPrefill.json',apps)
            marker={'directory':str(directory.relative_to(BASE)),'check':check or night,'night':night,
                    'finished':False,'status':'running','startedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
            try:
                self._container(directory,marker['check']); atomic_json(self.marker,marker)
            except Exception:
                shutil.rmtree(directory); raise

    def _finish(self, container):
        marker=load(self.marker,{})
        if not marker or marker.get('finished') or not container or container['State']['Running']: return
        directory=BASE/marker['directory']
        if not directory.resolve().is_relative_to((BASE/'jobs').resolve()): raise ValueError('Invalid job path')
        logs=log_text(JOB_CONTAINER)
        (BASE/'last-job.log').write_text(logs,encoding='utf8')
        failed=container['State'].get('ExitCode',1)!=0 or bool(re.search(r'Unexpected download error|Unable to download manifests|SteamLoginException|Skipping app',logs))
        result=load(directory/'successfullyDownloadedDepots.json',{})
        account=directory/'account.config'
        if account.exists():
            shutil.copy2(account,BASE/'prefill/account.config')
        main=BASE/'prefill/successfullyDownloadedDepots.json'
        merged=load(main,{})
        if isinstance(result,dict) and isinstance(merged,dict):
            merged.update(result); atomic_json(main,merged)
        # New manifest requests all happen before the long nightly chunk transfers.
        from zoneinfo import ZoneInfo
        if marker.get('night') and marker.get('check') and not failed and self.in_window(dt.datetime.now(ZoneInfo(TIMEZONE))):
            try:
                self._container(directory,False); marker['check']=False
                atomic_json(self.marker,marker); return
            except DockerError:
                failed=True
        marker.update(finished=True,status='failed' if failed else 'completed',finishedAt=dt.datetime.now(dt.timezone.utc).isoformat())
        atomic_json(self.marker,marker)
        # Jobs may contain refresh tokens. Only public logs and merged tracking are retained.
        if directory.exists(): shutil.rmtree(directory)

    def stop(self):
        with self.lock:
            current=inspect(JOB_CONTAINER)
            if current and current.get('Config',{}).get('Labels',{}).get('io.lanterncache.managed')!='true':
                raise DockerError('Refusing to stop a container not managed by LanternCache')
            marker=load(self.marker,{})
            marker['night']=False
            atomic_json(self.marker,marker)
            if current and current['State']['Running']: api('POST',f'/containers/{JOB_CONTAINER}/stop?t=10')
            self._finish(inspect(JOB_CONTAINER))

    def snapshot(self, now):
        with self.lock:
            cache=inspect(CACHE_CONTAINER); dns=inspect(DNS_CONTAINER); job=inspect(JOB_CONTAINER)
            settings=load(self.settings,{'nightEnabled':True})
            marker=load(self.marker,{})
            if job and job['State']['Running'] and marker.get('night') and not self.in_window(now):
                self.stop(); job=inspect(JOB_CONTAINER)
            self._finish(job)
            job=inspect(JOB_CONTAINER)
            # Once per local date, no catch-up downloads outside the approved window.
            if settings.get('nightEnabled',True) and self.in_window(now) and settings.get('lastNight')!=now.date().isoformat() and not (job and job['State']['Running']):
                if (BASE/'prefill/account.config').exists() and load(BASE/'prefill/selectedAppsToPrefill.json',[]):
                    try:
                        self.start(0,night=True)
                        settings['lastNight']=now.date().isoformat(); atomic_json(self.settings,settings)
                        job=inspect(JOB_CONTAINER)
                    except (ValueError,DockerError): pass
            active=[JOB_CONTAINER] if job and job['State']['Running'] else []
            marker=load(self.marker,{})
            logs=log_text(JOB_CONTAINER) if job else ((BASE/'last-job.log').read_text() if (BASE/'last-job.log').exists() else '')
            return {'online':bool(cache and cache['State']['Running'] and dns and dns['State']['Running']),
                    'nightEnabled':settings.get('nightEnabled',True),'nextRun':'','active':active,'logs':logs,
                    'jobStatus':'running' if active else marker.get('status','idle'),'jobMode':'check' if marker.get('check') else 'download'}
