import os
import subprocess
from itertools import islice

def get_procs():
	'''Returns a set of currently running processes.
	
	Process name is the contents of /proc/<pid>/comm - which is usually just the binary name.
	
	https://www.kernel.org/doc/html/latest/filesystems/proc.html#process-specific-subdirectories
	'''
	procs = set()
	for pid in os.listdir("/proc"):
		if not pid.isdigit():
			continue
		try:
			with open(f"/proc/{pid}/comm", "r") as file:
				comm = file.read().strip()
		except (PermissionError, OSError):
			continue
		procs.add(comm)
	return procs

def get_running_flatpaks():
	'''Returns a set of currently running flatpaks by parsing "flatpak ps"
	
	e.g. 'org.gnome.gitlab.somas.Apostrophe'
	'''
	result = subprocess.run(
		["flatpak", "ps", "--columns=application"],
		capture_output=True,
		text=True
	)
	apps = set()
	# islice skips skips the first line (which is a `header` from the ps results), and `update` bulk updates the set
	apps.update(islice(result.stdout.strip().splitlines(), 1, None))
	return apps
