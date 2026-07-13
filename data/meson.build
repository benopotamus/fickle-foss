desktop_file = i18n.merge_file(
        input: 'giving.fickle.foss.desktop.in',
       output: 'giving.fickle.foss.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'giving.fickle.foss.metainfo.xml.in',
       output: 'giving.fickle.foss.metainfo.xml',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

install_data('giving.fickle.foss.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])


service_conf = configuration_data()
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))
configure_file(
  input: 'giving.fickle.foss.service.in',
  output: 'giving.fickle.foss.service',
  configuration: service_conf,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

subdir('icons')

# Added by Ben 2026-06-22
custom_target(
  'compile-gschemas',
  input: 'giving.fickle.foss.gschema.xml',
  output: 'gschemas.compiled',
  command: [
    compile_schemas,
    '--targetdir', meson.current_build_dir(),
    meson.current_source_dir()
  ],
  build_by_default: true
)