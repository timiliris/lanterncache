"""Bounded private activity history; never stores request headers or credentials."""
import datetime as dt
import json
import re
import threading
import uuid
from runtime import BASE, atomic_json

def clean_log(value):
    value=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',str(value))
    lines=[line for line in value.splitlines() if not re.search(r'token|password|secret|steam.?guard|auth.?code|account\.config|@',line,re.I)]
    return '\n'.join(lines[-120:])[-12000:]

class Activity:
    def __init__(self,base=BASE):
        self.path=base/'ui-activity.json';self.lock=threading.RLock()
        try: self.data=json.loads(self.path.read_text(encoding='utf8'))
        except (OSError,ValueError): self.data={'events':[],'active':None}
        if not isinstance(self.data,dict) or not isinstance(self.data.get('events'),list): self.data={'events':[],'active':None}
    def save(self):
        self.data['events']=self.data['events'][-200:]
        atomic_json(self.path,self.data)
    def add(self,kind,status,**fields):
        with self.lock:
            item={'id':uuid.uuid4().hex,'kind':kind,'status':status,'at':dt.datetime.now(dt.timezone.utc).isoformat(),**fields}
            self.data['events'].append(item);self.save();return item
    def action(self,path,status,data):
        fields={'action':path.removeprefix('/api/')}
        if type(data.get('id')) is int: fields['app']=data['id']
        if type(data.get('enabled')) is bool: fields['enabled']=data['enabled']
        self.add('action','accepted' if status<400 else 'failed',**fields)
    def observe(self,state):
        with self.lock:
            jobs=list(state.get('active',[])); key='|'.join(sorted(jobs))
            current=next((e for e in self.data['events'] if e['id']==self.data.get('active')),None)
            changed=False
            if current and current.get('job')!=key:
                current['status']='failed' if state.get('jobStatus')=='failed' or current.get('hadFailure') else 'ended'
                current['endedAt']=state['timestamp']
                # Only managed final logs can safely belong to this session.
                if state.get('jobStatus') in ('failed','completed') or (not key and current.get('managed')):
                    current['logs']=clean_log(state.get('logs',''))
                    if re.search(r'Unexpected download error|Unable to download manifests|Skipping app|SteamLoginException',current['logs'],re.I): current['status']='failed'
                self.data['active']=None;current=None;changed=True
            if key and current is None:
                current=self.add('session','running',job=key,mode=state.get('jobMode','download'),managed=state.get('canStop') is not False,logs='')
                self.data['active']=current['id'];changed=True
            if current:
                logs=clean_log(state.get('logs',''))
                names=list(dict.fromkeys(current.get('games',[])+[g['name'] for g in state.get('games',[]) if g.get('status') in ('checking','downloading')]))
                if current.get('logs')!=logs or current.get('games')!=names:
                    current.update(logs=logs,games=names);changed=True
                    if re.search(r'Unexpected download error|Unable to download manifests|Skipping app|SteamLoginException',logs,re.I): current['hadFailure']=True
            if changed:self.save()
    def list(self):
        with self.lock:return [{k:v for k,v in event.items() if k not in ('logs','job')} for event in reversed(self.data['events'])]
    def detail(self,identifier):
        with self.lock:
            item=next((e for e in self.data['events'] if e['id']==identifier),None)
            return dict(item) if item else None
