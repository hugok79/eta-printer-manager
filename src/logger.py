import logging
import os
from pathlib import Path


def setup_logger():
    # Log dosyasını kullanıcının cache dizinine kaydeder
    log_dir = Path.home() / ".cache" / "eta-printer-manager"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
    except Exception:
        log_file = "/tmp/eta-printer-manager.log"

    log = logging.getLogger("eta_printer_manager")
    log.setLevel(logging.DEBUG)

    if not log.handlers:
        # Log Formatı: [Tarih Saat] [SEVİYE] [Dosya:Satır] - Mesaj
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. Dosyaya Yazıcı Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        # 2. Konsola Yazıcı Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)

    return log


# Modül seviyesinde 'logger' değişkenini tanımlıyoruz
logger = setup_logger()