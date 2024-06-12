from ..config import ARCHIVE_URL, TIMEZONE, TEAMS_BLACKLIST, ARCHIVE_TOKEN, REQUESTS_CLIENT, ARCHIVE_TOKEN_URL, HURRICANE_AUTH
from pydantic import BaseModel, constr, Json
from typing import Optional
from collections import Counter
import datetime, re
from requests.auth import HTTPBasicAuth

class Archive(BaseModel):
    cluster: Optional[constr(max_length=2500)] = ""
    description: Optional[constr(max_length=2500)] = ""
    technology: Optional[constr(max_length=64)] = ""
    username: Optional[constr(max_length=64)] = "AutoFix"
    team: Optional[constr(max_length=64)] = "TEAM"
    body: Optional[Json] = None
    report_type: Optional[constr(max_length=64)] = None

    @staticmethod
    async def verify_get_token():
        global ARCHIVE_TOKEN
        req = REQUESTS_CLIENT.get(f"{ARCHIVE_TOKEN_URL}/validate?token={ARCHIVE_TOKEN}", headers={"Authorization": ARCHIVE_TOKEN}, verify=False)
        if req.status_code != 200 or req.text == "false":
            ARCHIVE_TOKEN = REQUESTS_CLIENT.get(f"{ARCHIVE_TOKEN_URL}", headers={"Authorization": ARCHIVE_TOKEN}, auth=HTTPBasicAuth(HURRICANE_AUTH["username"], HURRICANE_AUTH["password"]), verify=False).text[1:][:-1]

    @staticmethod
    async def search(search, team, incidents):
        await Archive.verify_get_token()
        report_type = "incident"
        if not incidents:
            report_type = "alert"
        req = REQUESTS_CLIENT.post(f"{ARCHIVE_URL}/search/{team}/{report_type}", json={"search": search}, headers={"Authorization": ARCHIVE_TOKEN}, verify=False)
        return req.json()

    @staticmethod
    async def get_responsible_team(search: dict):
        count = Counter()
        teams = []
        for entry, value in search.items():
            count.update(re.findall("(\w+)\s*\([0-9]{4}\)\s*-", value[0]["Description"].replace("\\n", " ")))
            count.update(re.findall("\([0-9]{4}\)\s*(\w+)", value[0]["Description"].replace("\\n", " ")))
        for t in count:
            if count[t] > 2 or ((t[0] > 'a' and t[0] < 'z') or (t[0] > 'A' and t[0] < 'Z')):
                teams.append(t)
        return sorted(list(filter(lambda x: x not in TEAMS_BLACKLIST and x != search, teams)))

class ArchiveAlert(Archive):
    report_type: Optional[constr(max_length=64)] = "alert"
    actions_taken: Optional[constr(max_length=2500)] = ""

    async def check_if_exists(self):
        now = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        await Archive.verify_get_token()
        req = REQUESTS_CLIENT.get(url=f"{ARCHIVE_URL}/range/{self.team}/{now}/{now}", headers={"Authorization": ARCHIVE_TOKEN}, verify=False).json()
        for alert in req[next(iter(req))]:
            if await self.check_alert(alert):
                return True
        return False

    async def send_to_archive(self):
        await Archive.verify_get_token()
        self.body = {
            "@timestamp": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
            "cluster": self.cluster,
            "description": self.description,
            "report_type": self.report_type,
            "username": self.username
        }
        if await self.check_if_exists():
            return "Already Exists"
        req = REQUESTS_CLIENT.post(url=f"{ARCHIVE_URL}/{self.team}", json=self.body, verify=False, headers={"Authorization": ARCHIVE_TOKEN})
        return req.json()

class ArchiveIncident(Archive):
    report_type: Optional[constr(max_length=64)] = "incident"
    caid: Optional[constr(max_length=19)] = ""
    description: Optional[constr(max_length=2500)] = ""
    fix: Optional[constr(max_length=250)] = ""
    incident_type: Optional[constr(max_length=64)] = ""
    network: Optional[constr(max_length=64)] = ""
    symptom: Optional[constr(max_length=64)] = ""
    root_cause: Optional[constr(max_length=64)] = ""
    impact: Optional[constr(max_length=64)] = ""
    monitor: Optional[constr(max_length=64)] = ""
    clients: Optional[constr(max_length=64)] = ""
    error: Optional[constr(max_length=35)] = ""
    did_something: Optional[bool] = False
    hamalim: Optional[bool] = False
    escalation: Optional[bool] = False

    async def send_to_archive(self):
        await Archive.verify_get_token()
        self.body = {
            "@timestamp": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
            "caid": self.caid,
            "Description": self.description,
            "Fix": self.fix,
            "Incident Type": self.incident_type,
            "Network": self.network,
            "Symptom": self.symptom,
            "root cause": self.root_cause,
            "Impact": self.impact,
            "Monitor": self.monitor,
            "Technology": self.technology,
            "Clients": self.clients,
            "escalation": "Yes" if self.escalation else "No",
            "report_type": self.report_type,
            "@timestamp": datetime.datetime.now().strftime("%Y-%m-%d"),
            "username": self.username
        }
        req = REQUESTS_CLIENT.post(url=f"{ARCHIVE_URL}/{self.team}", json=[self.body], verify=False, headers={"Authorization": ARCHIVE_TOKEN})
        return await req.json()