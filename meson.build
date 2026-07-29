project('eta-printer-manager',
  version: '1.0.1',
  meson_version: '>= 0.50.0'
)

# 1. Ana dizinler
i18n = import('i18n')

# 2. Çalıştırılabilir ana betik (/usr/bin/eta-printer-manager olarak kurulur)
install_data('eta-printer-manager',
  install_dir: '/usr/bin'
)

# 3. Backend Python kodları
install_subdir('src',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 4. Arayüz Python kodları
install_subdir('ui',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 5. Stil ve Veri dosyaları
install_subdir('data',
  install_dir: '/usr/share/pardus/eta-printer-manager'
)

# 6. Masaüstü Kısayolu (.desktop)
install_data('data/eta-printer-manager.desktop',
  install_dir: '/usr/share/applications'
)

subdir('po')