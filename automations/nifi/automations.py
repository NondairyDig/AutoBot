import io, sys
from ...src.NiFi import NiFi
from ...src.Alert import Alert, AutoFix
from ...utils.task_manager import automation


@automation(total_steps="?", description="Checks Nifi Environments for Crashlooped Nodes and Fix Then", AutoFix=AutoFix(archive=True,
             conditions=Alert(application="nifi", message="has a disconnected node"),
             args={"cluster": {"message": r".*Environment (.*) has a disconnected node(.*)"}}))
def nifi_crashloop(self, cluster: str):
    self.update_progress(1, "Connecting To Cluster")
    clust = NiFi(name=cluster)
    self.update_progress(2, "Getting Crashlooped Nodes...")
    nodes = clust.get_nodes()
    output = {"CrashLopped": [], "ImagePullBackOffed": [], "Alreadyup": [], "Disconnected": [], "Can't Fix": []}
    self.update_progress(3, "Cleaning Up Problem Nodes...")
    current_step = 3
    for node in nodes:
        if node.state == "CrashLoopBackoff":
            self.update_progress(current_step, f"Fixing Crashlooped Node {node.name}")
            node.cleanup_and_reset_node()
            output["CrashLopped"].append(node.name)
        elif node.state == "ImagePullBackOff":
            self.update_progress(current_step, f"Fixing ImagePullBackOff Node {node.name}")
            node.delete_pod_force()
            output["ImagePullBackOffed"].append(node.name)
        elif not node.connected:
            try:
                clust.get_nifi_token()
                node.cluster_token = clust.token
                node.connect_node()
                self.update_progress(current_step, f"Connecting UP Node {node.name}")
                node.wait_for_node_to_connect()
                output["Disconnected"].append(node.name)
            except:
                output["Can't Fix"].append(node.name)
        else:
            output["Alreadyup"].append(node.name)
        current_step += 1
    return output if nodes else f"Couldn't get pods in {cluster}"


@automation(total_steps=3, description="Delete Any Pod from NiFi Cluster by force", AutoFix=False)
def acp_delete_pod_force(self, node: str):
    self.update_progress(1, "Connecting To Cluster")
    clust = NiFi.from_node(node)
    self.update_progress(2, "Getting Nodes")
    clust.get_nodes()
    self.update_progress(3, "Deleting Pod By Force")
    return [node for node in clust.nodes if node.name == node][0].delete_pod_force()


@automation(total_steps=7, description="Check /var/lib/nifi usage, and cleanup", AutoFix=AutoFix(archive=False,
             conditions=Alert(application="nifi", message="/var/lib/nifi"),
             args={"node": {"message": r"Instance (.*) is alerting with value [0-9]*.*"}}))
def clean_nifi_storage(self, node: str):
    self.update_progress(1, "Connecting To Cluster")
    clust = NiFi.from_node(node)
    self.update_progress(2, "Getting Nodes")
    clust.get_nodes()
    self.update_progress(3, "Checking Storage")
    try:
        storage_used = float(clust.get_storage_stats()[node]["flowfile"]["utilization"].removesuffix("%"))
    except:
        storage_used = 100.0
    if storage_used > 78:
        self.update_progress(4, "Cleaning Logs")
        list(filter(lambda n: n.name == node, clust.nodes))[0].clean_all_old_logs()
    try:
        self.update_progress(5, "Checking Storage")
        storage_used = float(clust.get_storage_stats()[node]["flowfile"]["utilization"].removesuffix("%"))
    except:
        storage_used = 100
    if storage_used > 90:
        self.update_progress(6, "Cleaning Journal")
        list(filter(lambda n: n.name == node, clust.nodes))[0].clean_journals()
    else:
        return f"Storage is not high enough to cleanup, current usage is {storage_used}%"
    return f"Cleaned Up {node}"