from ...utils.task_manager import automation 
from ...src.Alert import AlertScanner


@automation(description="Scan Alerts and Trigger AutoFix", AutoFix=False)
def autofix_scan_alerts(self):
	return AlertScanner.scan()