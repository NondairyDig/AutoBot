
from ...src.WhQ import QMGR
from ...src.Alert import AutoFix, Alert
from ...utils.task_manager import automation


@automation(total_steps=2, description="Clean DLQ on Queue Manager", AutoFix=AutoFix(archive=True,
                                                                        conditions=Alert(application="wmq", message="SYSTEM.DEAD.LETTER.QUEUE"),
                                                                        args={"queue_manager": {"node_name": "(.*):.*"}}))
def clean_dlq(self, queue_manager: str):
	self.update_progress(1, "Connecting to Queue Manager")
	qm = QMGR(queue_manager)
	self.update_progress(2, "Cleaning DLQ")
	qm.restore_from_dlq()
	return "Started Cleaning DLQ"


@automation(total_steps=2, description="Reset Channel", AutoFix=AutoFix(archive=True,
                                                        conditions=Alert(application="wmq", message="is retrying"),
                                                        args={"queue_manager": {"message": "The channel: .* on qmgr: (.*?) - is retrying"},
                                                                "channel": {"message": "The channel: .* on qmgr: (.*?) - is retrying"}}))
def channel_reset(self, queue_manager: str, channel: str):
	qm = QMGR(queue_manager)
	self.update_progress(1, "Connecting to Queue Manager")
	qm.connect()
	self.update_progress(2, "Resetting channel")
	qm.reset_channel(channel)
	qm.disconnect()
	return f"Channel: {channel} reset successfully"