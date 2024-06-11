
from ..config import ARCHIVE_URL, TIMEZONE, TEAMS BLACKLIST, ARCHIVE_TOKEN, REQUESTS CLIENT, ARCHIVE TOKEN_URL, HURRICANE AUTH
from pydantic import BaseModel, constr, 3son
from typing import Optional
from collections import Counter
from requests.auth import HTTPBasicAuth
ieport datetime, re
class Archive(Basemodel }:
cluster: Optional{constr(max_length=2500)] = 7"
description: Optional (conste(max_length=2500)] = “"
technology: Optional[constr(max_length-64)] = ""
username: Optional[constr(max_length=64)] = “AutoFix™
team: Optional [constr(max_length=64)] = “Hurricane”
body: Optional{Json] = Kone
report_type: Optional[constr(max_length=64)] = None
@staticnethod
async def verify get_token():
global ARCHIVE_TOKEN
req = REQUESTS_CLIENT.get (f"{ARCHIVE_TOKEN_URL}/validate?token={ARCHIVE_TOKEN}”, headers={"Authorization”: ARCHIVE TOKEN}, verify=False)
if req.status_code != 206 or req.text =~ “false”:
ARCHIVE_TOKEN = REQUESTS_CLIENT.get(f"{ARCHIVE_TOKEN_URL}”, headers-{"Authorization”: ARCHIVE_TOKEN}, auth-HTTPBasicauth(HURRICANE_AUTH[ “username” J, HURRICANE_AUTH["password"]), verify=False).text[{1:]
Gs-a)
@staticmethod
async def search(search, team, incidents):
await Archive.verify_get_token()
report_type = "incident" I
if not incidents:
report_type = “alert”
eq = REQUESTS. CLIENT. post (F"{ARCHIVE_URL}/search/{tean}/{report_type}”, json={"search”: search}, headers={"Authorization”: ARCHIVE_TOKEN}, verify=false)
return req.json(}
@staticmethod
async def get_responsible team(search: dict):
count. = Counter()
teams = []
for entry, value in search.items(}:
count update(re.findall("(\wt)\s*\([@-9]4\)\s*-{1}", value[@][“Oescription").replace(“\\n", “ ”)))
count .update(re. Findall("\([@-9]4\)\s*(\m+)", value[@]["Description”] replace("\\n", “ “}))
for t in count:
if count(t] > 2 or ((t[@] > ‘a’ and t[@] < 'z*) on (t{@] > ‘A’ and {0} < 'Z')):
teams.append(t)
return sorted(List(filter(lanbda x: x not in TEAMS_GLACKLIST or not x == search, teans)))
ene

IE Se
class ArchiveAlert(Archive):
report_type: Optional[constr(aax_length-64)] = “alert”
actions_taken: Optional[constr(max_length=250@)] = “"
def _init_(self, **date}:
Super().__init__(**data)
async def check_if_exists(self):
async def check_alert(alert):
for key, value in self .body.items():
if str(alert[key]) != str(value):
return False
return True
now = datetime, datetime.now( TIMEZONE) .strftime(“RY-Xm-Xd")
await Archive.verify_get_token()
req = REQUESTS_CLIENT.get(url-f" {ARCHIVE_URL}/range/{self.team}/{now}/{now}", headers={ "Authorization": ARCHIVE_TOKEN}, verify=False).json()
for alert in req{next(iter(req))]:
if await check_alert(alert):
return True
return False
async def send_to_srchive(self):
avait Archive.verify_get_token()
sel¥-hody = {
“@cimestamp": datetine.datetime.now(TIMEZONE) .strftine("XY-%m-Xd"),
“cluster": self.cluster,
“description”: self.description, I
“report_type”: self.report_type,
“usernane": self.username
t
if await seif.check_if_exists():
return "Already Exists”
req = REQUESTS. CLIENT. post (urlaf"{ARCHIVE_URL}/{self.team}”, jsone[self.body], verify-False, headers-{"Authorization": ARCHIVE TOKEN})
return req.json()
class ArchiveIncident (Archive) :
report_type: Optional[constr(max_length=64)] = “incident”
caid: Optional[constr(max_length=19)] = “*
description: optional[constr(max_length=25e2)] = ""
fix: Optional[conste{max_length=250)] = "”
incident_type: Optional [constr(max_length=64)] = “"
network: Optional [constr(max_length=64)] = “"
symptom: Optional [constr{max_length=64)] = ""
root_cause: Optional [constr(max_length=64)] = ""
impact: Optional[constr(max_length-64)] = “*
monitor: Optional {constr(max_length=64)} = ""
Ben icand owe

eh alana ae eee
root_cause: Optional [constr(max_length=64)] = ""
inpact: Optional{constr(max_length-64)] = "*
monitor: Optional {constr(max_length=64)] > ""
clients: Optional [constr(max_length-64)] = "”
error: Optional [constr(max_length=35)] = ""
did_sonething: Optional[bool] = False
hamalim: Optional{bool} = False
escalation: Optional[bool] = False
def __init_(self, **data):
super().__init__(**data)
async def send_to_archive(self):
await Archive.verify_get_token()
self body = {
"@timestamp": datetine.datetime now( TIMEZONE) . strftime("XY-Xm-Xd"),
"cAID": self-caid,
"Description": self.description,
"Fix": self.fix,
“Incident Type": self. incident_type,
“Network”: self.network,
“Symptom”: self.symptom,
“root cause”: self.root_cause,
“Inpact": self.impact,
“Monitor”: self.monitor,
“Technology”: self-technology,
“Clients”: self.clients,
“escelation": “Yes” if self.escalation else “No”,
“seport_type”: self.report_type,
“@tinestanp": datetine.datetime.now()-strftime("AV-ta-d"),
“username”: self-username
? I
req = REQUESTS_CLIENT. post (url=f"{ARCHIVE_URL}/{self.team}", json=[self.body], verify-False, headers-{"Authorization”: ARCHIVE_TOKEN})
return await req.json()