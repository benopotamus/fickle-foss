from gi.repository import Gio, Gdk, GLib
from .db import get_app_desktop_files

def get_app_icons():
	"""Returns a dictionary of Gdk.Texture's representing app icons. Texture's are retrieved from Fickle FOSS Tracker Gnome Extension via DBus. 
	
	We use DBus and the extension here to get around sandboxing in Flatpaks. When Fickle FOSS is run as a Flatpak, it doesn't have access to the icons (or desktop files) of other apps.
	 
	Dictionary structure is:
		{
			desktop_file: {
				'size64': Gdk.Texture,
				'size96': Gdk.Texture,
			},
			...
		}
	"""
	# https://api.pygobject.gnome.org/Gio-2.0/class-DBusProxy.html#gi.repository.Gio.DBusProxy
	proxy = Gio.DBusProxy.new_for_bus_sync(
		Gio.BusType.SESSION,
		Gio.DBusProxyFlags.NONE,
		None,
		'org.gnome.Shell',
		'/org/gnome/shell/extensions/FickleFossTracker1',
		'org.gnome.shell.extensions.FickleFossTracker1',
		None,
	)

	dbus_response = proxy.call_sync(
		'GetAppIcons',
		GLib.Variant('(as)', (get_app_desktop_files(),)),
		Gio.DBusCallFlags.NONE,
		-1,
		None,
	)

	# Note: If Fickle FOSS Tracker wasn't able to get the bytes for an icon (e.g. because the app has been deleted), it will have an empty List here (not None)
	app_icons = {}
	for appid, icons in dbus_response.unpack()[0].items():
		app_icons[appid] = {
			# We store the texture in app_icons (rather than the next step, a Gtk.Image) because textures can be reused and manipulated in multiple places, whereas manipulating an Image in one place affects that Image everywhere.
			'size64': Gdk.Texture.new_from_bytes(GLib.Bytes.new(bytes(icons['size64']))) if len(icons['size64']) else None,
			'size96': Gdk.Texture.new_from_bytes(GLib.Bytes.new(bytes(icons['size64']))) if len(icons['size96']) else None
		}
		#icon_image = Gtk.Image.new_from_paintable(texture)
	return app_icons

app_icons = get_app_icons()
