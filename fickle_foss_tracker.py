#!/usr/bin/python3

import utils
import time
import os

DESKTOP_APP_DIRS = [
	"/usr/share/applications",
	"/usr/local/share/applications",
	os.path.expanduser("~/.local/share/applications"),
] + utils.get_flatpak_desktop_dirs()
DESKTOP_FILES = utils.load_desktop_files(DESKTOP_APP_DIRS)
POLL_INTERVAL = 10  # seconds
DB_PATH = os.path.expanduser("~/.local/share/fickle_foss/fickle_foss.db")
conn = utils.init_db(DB_PATH)

while True:
	new_processes, running_pids = utils.get_new_processes()
	new_desktop_apps = utils.filter_to_desktop_apps(new_processes, running_pids, DESKTOP_FILES)
	if new_desktop_apps:
		for app in new_desktop_apps:
			# print(app['app_name'])
			utils.log_launch(conn, app)
	time.sleep(POLL_INTERVAL)