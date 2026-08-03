project('eta-printer-manager',
  version: '1.0.2',
  meson_version: '>= 0.50.0'
)

# 1. Imports and modules
i18n = import('i18n')

# 2. Main executable script (installed to /usr/bin/eta-printer-manager)
install_data('eta-printer-manager',
  install_dir: '/usr/bin'
)

# 3. Backend Python source code
install_subdir('src',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 4. UI Python source code
install_subdir('ui',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 5. Style and data files
install_subdir('data',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 6. Desktop entry shortcut (.desktop)
install_data('data/eta-printer-manager.desktop',
  install_dir: '/usr/share/applications'
)

# 7. App icon
install_data('data/eta-printer-manager.svg',
  install_dir: '/usr/share/icons/hicolor/scalable/apps'
)

subdir('po')
