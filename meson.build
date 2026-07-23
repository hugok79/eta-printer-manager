project('pardus-printers',
  version: '1.0.0',
  meson_version: '>= 0.50.0'
)

# 1. Ana dizinler
i18n = import('i18n')

# 2. Çalıştırılabilir ana betik (/usr/bin/pardus-printers olarak kurulur)
install_data('pardus-printers',
  install_dir: '/usr/bin'
)

# 3. Backend Python kodları
install_subdir('src',
  install_dir: '/usr/share/pardus/pardus-printers'
)

# 4. Arayüz Python kodları
install_subdir('ui',
  install_dir: '/usr/share/pardus/pardus-printers'
)

# 5. Stil ve Veri dosyaları
install_subdir('data',
  install_dir: '/usr/share/pardus/pardus-printers'
)

# 6. Masaüstü Kısayolu (.desktop)
install_data('data/pardus-printers.desktop',
  install_dir: '/usr/share/applications'
)

subdir('po')