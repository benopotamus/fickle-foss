import os
import glob
import configparser
import subprocess


# Sometimes the Exec name in the desktop file doesn't exactly match the value in the /proc/<pid>/comm file
# This dictionary is used to rename the exec value so it will match
exec_renames = {
	'libreoffice': 'soffice.bin',
	'thunderbird': 'thunderbird-bin'
}


def get_app_map_from_desktop_files(desktop_apps_dirs):
	'''Returns two dictionaries based on `.desktop` files:

	1) mapping of app names to Exec values (Exec value is dictionary key)
		Uses a truncated Exec value to match the truncated value in /proc/<pid>/comm
		e.g. { '/usr/lib64/libreoffice/program/soffice.bin': 'LibreOffice' }
	
	2) mapping of app names to X-Flatpak values (X-Flatpak is dictionary key)
		e.g. { 'org.gnome.gitlab.somas.Apostrophe': 'Apostrophe' }
	'''
	proc_apps = {}
	flatpak_apps = {}

	for directory in desktop_apps_dirs:
		for filepath in glob.glob(os.path.join(directory, "*.desktop")):
			try:
				cp = configparser.ConfigParser(interpolation=None, strict=False)
				cp.read(filepath, encoding="utf-8")

				if not cp.has_section("Desktop Entry"):
					continue

				entry = cp["Desktop Entry"]

				if entry.get("Type", "") != "Application":
					continue

				app_name = entry.get("Name", "").strip()
				app_flatpak = entry.get("X-Flatpak", "").strip() # e.g. org.gnome.gitlab.somas.Apostrophe

				if app_flatpak:
					flatpak_apps[app_flatpak] = app_name
				
				else:
					# We do a few things here to get just the file name
					# 	1. Strip spaces
					# 	2. Split on spaces (seperates file name from command line arguments)
					# 	3. Split on "/" because some Exec entries are full paths, but the value in /proc/<pid>/comm is always just a file name (no path). 
					# 	4. The [-1] grabs the file name at the end of the path
					app_exec = entry.get("Exec", "").strip().split()[0].split('/')[-1]

					# Special processing for popular apps where the desktop exec value is not the same as the /proc/<pid>/comm value that it needs to match on
					if app_exec in exec_renames:
						app_exec = exec_renames[app_exec]

					# The Exec value is eventually compared to /proc/<pid>/comm value. The comm value has a max length of 15 characters so we truncate it here
					# See https://www.kernel.org/doc/html/latest/filesystems/proc.html#proc-pid-comm-proc-pid-task-tid-comm
					proc_apps[app_exec[:15]] = app_name

					# TODO maybe update this data structure to be:
					# { 'app_name': ?, 'app_exec': ?, 'app_icon': ? }

			except Exception:
				# Skip all failures 🤷
				continue

	return proc_apps, flatpak_apps


def get_flatpak_desktop_dirs():
	"""
	Asks flatpak for all configured installation paths and returns the
	exports/share/applications subdirectory for each one that exists.
	Returns an empty list if flatpak is not installed.
	"""
	dirs = []
	try:
		result = subprocess.run(
			["flatpak", "--installations"],
			capture_output=True, text=True, timeout=5
		)
		for line in result.stdout.splitlines():
			base = line.strip()
			candidate = os.path.join(base, "exports", "share", "applications")
			if os.path.isdir(candidate):
				dirs.append(candidate)
	except FileNotFoundError:
		pass  # flatpak not installed
	print(dirs)
	return dirs


def get_current_desktop():
	"""
	Returns the current desktop environment as reported by XDG_CURRENT_DESKTOP,
	e.g. "Gnome", "KDE", "XFCE".
	Returns None if not set.
	"""
	desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
	return desktop if desktop else None
