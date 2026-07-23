import cups
import os
import subprocess

class CupsBackend:
    def __init__(self):
        try:
            self.conn = cups.Connection()
        except Exception as e:
            print(f"CUPS bağlantı hatası: {e}")
            self.conn = None

    def get_printers(self):
        if not self.conn:
            return {}
        try:
            return self.conn.getPrinters()
        except Exception as e:
            print(f"Yazıcılar alınamadı: {e}")
            return {}

    def get_printer_jobs(self, printer_name):
        if not self.conn:
            return {}
        try:
            jobs = self.conn.getJobs(
                my_jobs=False,
                requested_attributes=["job-id", "job-name", "job-state", "printer-uri", "job-originating-user-name"]
            )
            return {k: v for k, v in jobs.items() if printer_name in v.get('printer-uri', '')}
        except Exception as e:
            print(f"İşler alınamadı: {e}")
            return {}

    def cancel_job(self, job_id):
        if not self.conn:
            return False
        try:
            self.conn.cancelJob(job_id)
            return True
        except Exception as e:
            print(f"İş iptal edilemedi: {e}")
            return False

    def pause_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.disablePrinter(printer_name)
            return True
        except Exception as e:
            print(f"Yazıcı duraklatılamadı: {e}")
            return False

    def resume_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.enablePrinter(printer_name)
            return True
        except Exception as e:
            print(f"Yazıcı devam ettirilemedi: {e}")
            return False

    def get_ppds(self):
        if not self.conn:
            return {}
        try:
            return self.conn.getPPDs()
        except Exception as e:
            print(f"PPD'ler alınamadı: {e}")
            return {}

    def print_test_page(self, printer_name):
        if not self.conn:
            return False
        test_file_path = "/tmp/pardus_test_page.txt"
        try:
            with open(test_file_path, "w") as f:
                f.write("Pardus Yazıcı Test Sayfası\n\nBu sayfa başarıyla yazdırıldıysa, yazıcınız düzgün çalışıyor demektir.\n")
            job_id = self.conn.printFile(printer_name, test_file_path, "Test Page", {})
            return job_id > 0
        except Exception as e:
            print(f"Test sayfası yazdırılamadı: {e}")
            return False

    def delete_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.deletePrinter(printer_name)
            return True
        except Exception as e:
            print(f"Yazıcı silinemedi: {e}")
            return False

    def get_default_printer(self):
        if not self.conn:
            return None
        try:
            return self.conn.getDefault()
        except Exception as e:
            print(f"Varsayılan yazıcı alınamadı: {e}")
            return None

    def set_default_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            subprocess.run(['lpoptions', '-d', printer_name], check=True)
            return True
        except Exception as e:
            print(f"Varsayılan yazıcı yapılamadı: {e}")
            return False

    def discover_devices(self):
        if not self.conn:
            return {}
        try:
            return self.conn.getDevices()
        except Exception as e:
            print(f"Cihazlar keşfedilemedi: {e}")
            return {}

    def add_printer(self, name, uri, ppd_name="everywhere"):
        if not self.conn:
            return False
        try:
            cmd = ['pkexec', '/usr/sbin/lpadmin', '-p', name, '-E', '-v', uri, '-m', ppd_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Yazıcı eklenirken hata: {e}")
            return False

    def get_printer_state(self, printer_name):
        if not self.conn:
            return "unknown"
        try:
            printers = self.conn.getPrinters()
            if printer_name in printers:
                state = printers[printer_name].get('printer-state', 0)
                state_map = {3: 'idle', 4: 'printing', 5: 'stopped'}
                return state_map.get(state, 'unknown')
            return "unknown"
        except Exception as e:
            return "unknown"