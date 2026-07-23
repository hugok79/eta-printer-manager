import subprocess
import re

class ScannerBackend:
    def __init__(self):
        pass

    def get_scanners(self):
        scanners = {}
        try:
            result = subprocess.run(['scanimage', '-L'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout
                pattern = re.compile(r"device `([^']+)' is a (.*)")
                for line in output.splitlines():
                    match = pattern.search(line)
                    if match:
                        device_id = match.group(1)
                        description = match.group(2)
                        
                        scanners[device_id] = {
                            'printer-state-message': 'Hazır (Tarayıcı)',
                            'device-class': 'scanner',
                            'description': description
                        }
            return scanners
        except FileNotFoundError:
            print("Tarayıcı sistemi (SANE) bulunamadı.")
            return {}
        except Exception as e:
            print(f"Tarayıcılar alınamadı: {e}")
            return {}