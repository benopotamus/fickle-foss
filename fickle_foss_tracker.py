#!/usr/bin/python3

'''Fickle FOSS (command line version)

This is the command line version of Fickle FOSS. Eventually there will be a GUI version that uses the same service (for tracking running apps) and the same database.

The gist of how this program works is:
	* On load, the program searches through DESKTOP_FILE_DIRS and finds all `*.desktop` files
	* For each file, it works out if it is a Flatpak or regular program, and it holds in memory an identifier - the URI for Flatpaks or the file name in the Exec line of the desktop file

	* Every POLL_INTERVAL (i.e. 10 seconds), the program scans `/proc` and queries `flatpak` to determine which apps are currently running
	* Each running app is matched against the identifier from the desktop file (the URI or Exec file name) and the app name and desktop file are logged in the database

There's a little complexity around matching the /proc values because it is based on the `comm` file, which is truncatced to 15 characters long, and sometimes the value in Exec doesn't quite match the value in comm.

The desktop file name is logged in the database so the GUI app can eventually use it to retreive the file and get things like the app icon for display.
'''

import os, datetime, time
from pathlib import Path

import tracker_utils.desktop_file_scan as desktop_file_scan
import tracker_utils.app_scan as app_scan
import tracker_utils.db as db

POLL_INTERVAL = 10  # seconds
DB_PATH = Path.home() / ".local" / "share" / "fickle-foss" / "fickle-foss.db"


conn = db.init_db(DB_PATH)

# Get directories that contain .desktop files
# .desktop files seem to all be inside dirs from XDG_DATA_HOME and/or XDG_DATA_DIRS - so we used those
xdg_dirs = [Path(path) / "applications" for path in os.environ['XDG_DATA_HOME'].split(':')] + [Path(path) / "applications" for path in os.environ['XDG_DATA_DIRS'].split(':')]

# Flatpaks and package manager installed apps are processed differently (different matching criteria etc) so we have two maps
proc_apps_map, flatpak_apps_map = desktop_file_scan.get_maps(xdg_dirs)

current_day = None
while True:
	# Fickle FOSS reports on how many *days* an application was used in a period, so we start a new todays_procs if the date has changed
	if current_day != datetime.date.today():
		current_day = datetime.date.today() # This also sets the date on initial load
		todays_procs = set()
		todays_flatpaks = set()

	# Get sets of running processes and running flatpaks
	running_procs = app_scan.get_procs()
	running_flatpaks = app_scan.get_running_flatpaks()

	for proc in running_procs:
		if proc not in todays_procs and proc in proc_apps_map:
			todays_procs.add(proc)
			db.log_app(conn, proc_apps_map[proc]) # Map entries are dictionaries containing `app_name` and `desktop_file_name`

	for flatpak in running_flatpaks:
		if flatpak not in todays_flatpaks and flatpak in flatpak_apps_map:
			todays_flatpaks.add(flatpak)
			db.log_app(conn, flatpak_apps_map[flatpak])

	time.sleep(POLL_INTERVAL)
