project('eta-printer-manager',
  version: '1.0.1',
  meson_version: '>= 0.50.0'
)

i18n = import('i18n')

# 1. Translation directory
subdir('po')

# 2. Extract version from debian/changelog and generate __version__ file
output_file = '__version__'
cmd = ['bash', '-c', 'head -n 1 debian/changelog | sed "s/.*(//g;s/).*//g" > ' + meson.current_build_dir() + '/__version__']
run_command(cmd, check: true)

install_data(
  meson.current_build_dir() / output_file,
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 3. Main executable script (installed to /usr/bin/eta-printer-manager)
install_data('eta-printer-manager',
  install_dir: '/usr/bin'
)

# 4. Backend Python source code
install_subdir('src',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 5. UI Python source code
install_subdir('ui',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 6. Style and data files
install_subdir('data',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 7. Desktop entry shortcut (.desktop)
install_data('data/eta-printer-manager.desktop',
  install_dir: '/usr/share/applications'
)

# 8. Application icon for system theme
install_data('data/eta-printer-manager.svg',
  install_dir: '/usr/share/icons/hicolor/scalable/apps'
)