import os
import glob
import configparser
import subprocess


# Special overrides for libreoffice
# Maps a .desktop file's `Exec=` binary name to the comm name seen in `/proc`
_BINARY_ALIASES = {
	"libreoffice":         "soffice",
	"libreoffice-writer":  "soffice",
	"libreoffice-calc":    "soffice",
	"libreoffice-impress": "soffice",
	"libreoffice-draw":    "soffice",
}

def load_desktop_files(desktop_app_dirs):
	"""
	Parses .desktop files and returns a dict mapping known executable/comm
	names to their friendly app names.

	e.g. {
		"firefox":          "Firefox Web Browser",
		"soffice":          "LibreOffice",
		"soffice --writer": "LibreOffice Writer",
	}
	"""
	apps = {}
	current_desktop = get_current_desktop()

	for directory in desktop_app_dirs:
		for filepath in glob.glob(os.path.join(directory, "*.desktop")):
			try:
				cp = configparser.ConfigParser(interpolation=None, strict=False)
				cp.read(filepath, encoding="utf-8")

				if not cp.has_section("Desktop Entry"):
					continue

				entry = cp["Desktop Entry"]

				if entry.get("Type", "") != "Application":
					continue
				if entry.get("NoDisplay", "false").lower() == "true":
					continue

				if current_desktop:
					only_show_in = entry.get("OnlyShowIn", "")
					if only_show_in and current_desktop not in only_show_in.split(";"):
						continue

					not_show_in = entry.get("NotShowIn", "")
					if current_desktop in not_show_in.split(";"):
						continue

				name = entry.get("Name", "").strip()
				exec_line = entry.get("Exec", "").strip()

				if not name or not exec_line:
					continue

				# Strip field codes (%u, %F, etc.)
				tokens = [t for t in exec_line.split() if not t.startswith("%")]
				if not tokens:
					continue

				binary = os.path.basename(tokens[0])

				# For Flatpak apps, the real command is in --command=<name>
				if binary == "flatpak":
					command_arg = next((t for t in tokens if t.startswith("--command=")), None)
					if command_arg:
						binary = command_arg.split("=", 1)[1]
					else:
						continue

				# Normalise known wrapper binaries to the real comm name
				binary = _BINARY_ALIASES.get(binary, binary)

				# Primary key: just the executable name
				apps.setdefault(binary, name)

				# Truncated key: handles kernel's 15-char comm limit in /proc/comm
				if len(binary) > 15:
					apps.setdefault(binary[:15], name)

				# Suite key: executable + first flag, for apps like LibreOffice
				flags = [t for t in tokens[1:] if t.startswith("--")]
				if flags:
					apps.setdefault(f"{binary} {flags[0]}", name)

			except Exception:
				continue

	return apps


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
	return dirs


def get_current_desktop():
	"""
	Returns the current desktop environment as reported by XDG_CURRENT_DESKTOP,
	e.g. "GNOME", "KDE", "XFCE".
	Returns None if not set.
	"""
	desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
	# XDG_CURRENT_DESKTOP can be colon-separated e.g. "ubuntu:GNOME"
	# Claude made this decision
	return desktop.split(":")[0] if desktop else None
