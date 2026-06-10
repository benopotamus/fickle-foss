import os
import glob
import configparser


# Sometimes the Exec name in the desktop file doesn't exactly match the value in the /proc/<pid>/comm file
# This dictionary is used to rename the exec value so it will match
exec_renames = {
	'libreoffice': 'soffice.bin',
	'thunderbird': 'thunderbird-bin'
}

def get_maps(dirs):
	'''Returns two dictionaries based on `.desktop` files:

	1) mapping of app names to Exec values (Exec value is dictionary key)
		Uses a truncated Exec value to match the truncated value in /proc/<pid>/comm
		e.g. { '/usr/lib64/libreoffice/program/soffice.bin': 'LibreOffice' }
	
	2) mapping of app names to X-Flatpak values (X-Flatpak is dictionary key)
		e.g. { 'org.gnome.gitlab.somas.Apostrophe': 'Apostrophe' }
	'''
	proc_apps = {}
	flatpak_apps = {}

	for directory in dirs:
		for filepath in glob.glob(os.path.join(directory, "*.desktop")):
			filename = os.path.basename(filepath)

			cp = configparser.ConfigParser(interpolation=None, strict=False)
			cp.read(filepath, encoding="utf-8")

			if not cp.has_section("Desktop Entry"):
				continue

			entry = cp["Desktop Entry"]

			if entry.get("Type", "") != "Application":
				continue

			app_name = entry.get("Name", "").strip()
			app_flatpak = entry.get("X-Flatpak", "").strip() # e.g. org.gnome.gitlab.somas.Apostrophe

			# Add to Flatpak apps map, but not if it is already in the map because the user may have created their own version of a .desktop file (in their home directory) to override the Flatpak provided one.
			if app_flatpak and app_flatpak not in flatpak_apps:
				flatpak_apps[app_flatpak] = {
					'app_name': app_name,
					'desktop_file_name': filename, # The desktop filename will be used by the eventual GUI app to get the app icon
				}
			
			else:
				# We do a few things here to get just the file name
				# 	1. Strip spaces
				# 	2. Split on spaces (seperates file name from command line arguments)
				# 	3. Split on "/" because some Exec entries are full paths, but the value in /proc/<pid>/comm is always just a file name (no path). 
				# 	4. The [-1] grabs the file name at the end of the path
				app_exec = entry.get("Exec", "").strip().split()[0].split('/')[-1]

				# Special processing for popular apps. Renames the desktop file exec value to one that matches the corresponding value in /proc/<pid>/comm
				if app_exec in exec_renames:
					app_exec = exec_renames[app_exec]

				# The Exec value is eventually compared to /proc/<pid>/comm value. The comm value has a max length of 15 characters so we truncate it here
				# See https://www.kernel.org/doc/html/latest/filesystems/proc.html#proc-pid-comm-proc-pid-task-tid-comm
				proc_apps[app_exec[:15]] = {
					'app_name': app_name,
					'desktop_file_name': filename,
				}

	return proc_apps, flatpak_apps

# def get_current_desktop():
# 	"""
# 	Returns the current desktop environment as reported by XDG_CURRENT_DESKTOP,
# 	e.g. "Gnome", "KDE", "XFCE".
# 	Returns None if not set.
# 	"""
# 	desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
# 	return desktop if desktop else None
