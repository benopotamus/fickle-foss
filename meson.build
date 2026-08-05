project('fickle-foss',
          version: '0.1.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')




subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
  glib_compile_schemas: true,
  # gtk_update_icon_cache: true, # Commented out to resolve an error
  update_desktop_database: true,
)


# Ask the running session bus to reload its config so it picks up the new
# giving.fickle.foss.service file immediately, without requiring a logout.
# The trailing '; true' means a missing gdbus or absent session bus can
# never fail the install.
#
# See also https://github.com/mesonbuild/meson/issues/14202
meson.add_install_script(
  'sh', '-c',
  'command -v gdbus >/dev/null 2>&1 && ' +
  'gdbus call --session --dest org.freedesktop.DBus ' +
  '--object-path /org/freedesktop/DBus ' +
  '--method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1; true',
  skip_if_destdir: true,
)