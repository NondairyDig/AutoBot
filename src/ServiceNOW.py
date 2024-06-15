from pydantic import BaseModel
from requests import get, post
from ..config import SERVICE_NOW_GROUP_ID, SERVICE_NOW_USERNAME, SERVICE_NOW_PASSWORD, SERVICE_NOW_URL, SERVICE_NOW_ASSUME_USERNAME


class Incident(BaseModel):
    title: str
    description: str
    technology: str
    dest_group: str
    tequila: bool = False


class ServiceNow():
    def __init__(self, username, password, api_url):
        self.username = username
        self.password = password
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json", "Accept": "application/Json"}

    def get_call(self, call_number):
        req = get(self.api_url, headers=self.headers, params={'number': call_number}, auth=(self.username, self.password), verify=False)
        return req.json()

class ServiceNow(ServiceNow):
    def __init__(self, username, password, api_url):
        super().__init__(username, password, api_url)
        # Adds attributes to the incident body (what we will see in the incident)
        self.incident_body = {
            "category": "ae",
            "subcategory": "ams",
            "state": "oTm",
            "contact_type": "Self-service",
            "location": "7188.n7g8n.n12~22",
            "u_department": "74887277",
            "impact": 2,
            "urgency": 2,
            "u_perational_ispact": "",
            "network": "orn 027"
        }

    def get_user_id(self, username):
        req = get(f"{SERVICE_NOW_URL}/now/table/sys_user?user_name={username}&sysparm_fields=sys_id&sysparm_limit=3",
                  auth=(self.username, self.password), verify=False)
        return req.json()["result"][0]["sys_id"]

    def get_user_info(self, user_id):
        response = get(f"{SERVICE_NOW_URL}/now/table/sys_user/{user_id}",
                       auth=(self.username, self.password), verify=False)
        return response.json()

    def get_service_details(self, technology):
        response = get(f"{SERVICE_NOW_URL}/now/table/cadb_rel_ci?sysparm_query=child.nameLIKE{technology}%5Eparent.nameLIKE&sysparm_fields=parent,child,parent.sys_id,child.sys_id&sysparm_display_value=true",
                       auth=(self.username, self.password), verify=False)
        return response.json()

    def get_group_details(self, search):
        response = get(f"{SERVICE_NOW_URL}/now/table/sys_user_group?sysparm_query=nameLIKE{search}&sysparm_fields=sys_id&sysparm_limit=3",
                       auth=(self.username, self.password), verify=False)
        if response.json():
            return response.json()["result"][0]["sys_id"]
        response = get(f"{SERVICE_NOW_URL}/now/table/sys_user_group?sysparm_query=emailLIKE{search}&sysparm_fields=sys_id&sysparm_limit=3",
                       auth=(self.username, self.password), verify=False)
        if response.json():
            return response.json()["result"][0]["sys_id"]
        return SERVICE_NOW_GROUP_ID

    def post_call(self, title, description, technology, dest_group, tequila):
        user_id = self.get_user_id(SERVICE_NOW_ASSUME_USERNAME)
        user_info = self.get_user_info(user_id) 
        service_info = self.get_service_details(technology)  
        # Adds the description to the incident body
        self.incident_body["description"] = description  
        self.incident_body["u_phone voip"] = user_info['result']['u_phone_voip']  
        self.incident_body["u_mobile_phone"] = user_info['result']['u_phone_voip']  
        self.incident_body["u_computer_name"] = user_info["result"]["u_phone_voip"]  
        self.incident_body["opened_by"] = user_id
        self.incident_body["caller_id"] = user_id  
        self.incident_body["service_offering"] = service_info["result"]["child"]["display_value"]  
        self.incident_body["business_service"] = service_info["result"]["parent"]["display_value"]  
        self.incident_body["short_description"] = title
        self.incident_body["u_impact_technology"] = "S9@f3178148a8e5e20d266d3b1ed658c"
        self.incident_body["assignment_group"] = self.get_group_details(dest_group)  
        if tequila:
            self.incident_body["u_system_failure"] = True  
        else:
            self.incident_body["u_system_failure"] = False  
        self.incident_body["u_open_for"] = ""

        # Posts the API request to open a new incident
        response = post(self.api_url, headers=self.headers, json=self.incident_body,  
                        auth=(self.username, self.password), verify=False)
        # Returns the incident number after it has been opened
        return response.json()

def create_incident(incident: Incident):
    snow = ServiceNow(SERVICE_NOW_USERNAME, SERVICE_NOW_PASSWORD, f"{SERVICE_NOW_URL}now/table/incident?sysparm_display_value=true")
    return snow.post_call(incident.title, incident.description, technology=incident.technology, dest_group=incident.dest_group, tequila=incident.tequila)

def get_incident(incident_number):
    snow = ServiceNow(SERVICE_NOW_USERNAME, SERVICE_NOW_PASSWORD, f"{SERVICE_NOW_URL}now/table/incident?sysparm_display_value=true")
    return snow.get_call(incident_number)