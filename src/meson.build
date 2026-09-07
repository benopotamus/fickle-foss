pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'fickle_foss'
gnome = import('gnome')

gnome.compile_resources('fickle-foss',
  'fickle-foss.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'fickle-foss.in',
  output: 'fickle-foss',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

fickle_foss_sources = [
  '__init__.py',
  'main.py',
  'db.py',
  'helpers.py',
  'state.py',

  'window.py',
  'preferences_dialog.py',

  'donations_page.py',

  'donate_page.py',
  'donation_dialog.py',
]

install_data(fickle_foss_sources, install_dir: moduledir)
