# pyrefly: ignore [missing-import]
import os
import cups
import webbrowser
import subprocess
from src.logger import logger

class CupsBackend:
    def __init__(self):
        try:
            self.conn = cups.Connection()
            logger.info("CUPS connection established successfully.")
        except Exception as e:
            logger.error(f"CUPS connection error: {e}")
            self.conn = None

    def get_printers(self):
        logger.debug("Fetching printer list from CUPS...")
        try:
            # Thread-safe: For background threads, create an independent connection
            conn = cups.Connection()
            printers = conn.getPrinters()
            logger.debug(f"Found {len(printers)} printers.")
            return printers
        except Exception as e:
            logger.exception("Failed to fetch printer list from CUPS.")
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
            logger.error(f"Failed to fetch print jobs: {e}")
            return {}

    def cancel_job(self, job_id):
        if not self.conn:
            return False
        try:
            self.conn.cancelJob(job_id)
            logger.info(f"Job {job_id} cancelled successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def pause_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.disablePrinter(printer_name)
            logger.info(f"Printer '{printer_name}' paused.")
            return True
        except Exception as e:
            logger.error(f"Failed to pause printer '{printer_name}': {e}")
            return False

    def resume_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.enablePrinter(printer_name)
            logger.info(f"Printer '{printer_name}' resumed.")
            return True
        except Exception as e:
            logger.error(f"Failed to resume printer '{printer_name}': {e}")
            return False

    def get_ppds(self):
        logger.debug("Fetching PPD list from CUPS...")
        try:
            # Thread-safe: For background threads, create an independent connection
            conn = cups.Connection()
            ppds = conn.getPPDs()
            logger.debug(f"Found {len(ppds)} PPD drivers.")
            return ppds
        except Exception as e:
            logger.error(f"Failed to fetch PPD drivers: {e}")
            return {}

    def find_best_ppd(self, model_name, device_uri=""):
        """
        Scans the system for PPDs using normalized manufacturer/model matching
        and multi-token fuzzy search.
        """
        default_ppd = "drv:///sample.drv/generic.ppd"
        if not model_name:
            return default_ppd

        ppds = self.get_ppds()
        if not ppds:
            return default_ppd

        import re

        def normalize(text):
            """Removes all non-alphanumeric characters for clean comparison."""
            return re.sub(r'[^a-z0-9]', '', text.lower())

        target_raw = model_name.strip().lower()
        target_clean = normalize(model_name)

        # 1. Exact Match Check
        for ppd_key, ppd_info in ppds.items():
            make_model = ppd_info.get("ppd-make-and-model", "").strip().lower()
            make_model_clean = normalize(make_model)

            if target_raw == make_model or target_clean == make_model_clean:
                logger.info(f"Exact PPD match found for '{model_name}': {ppd_key}")
                return ppd_key

        # Remove noise words (like 'series', 'driver', 'printer') to extract core model code
        noise_words = {"series", "driver", "cups", "printer", "hpcups", "brlaser", "pcl"}
        target_words = set(re.findall(r'[a-z0-9]+', target_raw)) - noise_words

        best_ppd = None
        best_score = 0

        # 2. Token-Based Fuzzy Search
        for ppd_key, ppd_info in ppds.items():
            make_model = ppd_info.get("ppd-make-and-model", "").strip().lower()
            make_model_clean = normalize(make_model)

            # Substring match (normalized)
            if (len(target_clean) > 4 and target_clean in make_model_clean) or \
               (len(make_model_clean) > 4 and make_model_clean in target_clean):
                logger.info(f"Normalized substring PPD match found for '{model_name}': {ppd_key}")
                return ppd_key

            # Score by matching individual model tokens (e.g. "brother" and "l2700dw")
            ppd_words = set(re.findall(r'[a-z0-9]+', make_model)) - noise_words
            matching_tokens = target_words.intersection(ppd_words)

            if len(matching_tokens) > best_score:
                best_score = len(matching_tokens)
                best_ppd = ppd_key

        # If we matched at least 2 significant terms (e.g., mark + model code)
        if best_ppd and best_score >= 2:
            logger.info(f"Fuzzy PPD match found for '{model_name}': {best_ppd} (score: {best_score})")
            return best_ppd

        # 3. Fallback to Driverless IPP Everywhere for Network/IPP Printers
        if device_uri and device_uri.startswith(("ipp://", "ipps://", "http://", "https://")):
            logger.info(f"Network device detected. Using IPP Everywhere driverless fallback for '{model_name}'.")
            return "everywhere"

        logger.info(f"No matching PPD found for '{model_name}'. Falling back to Generic PostScript.")
        return default_ppd

    def print_test_page(self, printer_name):
        if not self.conn:
            return False
        
        # 1. Standard color/logo CUPS test page path
        test_file_path = "/usr/share/cups/data/testprint"
        
        # 2. If this file doesn't exist on the system, fall back to the old simple text file
        if not os.path.exists(test_file_path):
            test_file_path = "/tmp/pardus_test_page.txt"
            with open(test_file_path, "w") as f:
                f.write("Pardus Printer Test Page\n\nIf this page prints successfully, your printer is working correctly.\n")

        try:
            job_id = self.conn.printFile(printer_name, test_file_path, "Test Page", {})
            logger.info(f"Test page job {job_id} sent to '{printer_name}'.")
            return job_id > 0
        except Exception as e:
            logger.error(f"Failed to print test page on '{printer_name}': {e}")
            return False

    def delete_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.deletePrinter(printer_name)
            logger.info(f"Printer '{printer_name}' deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete printer '{printer_name}': {e}")
            return False

    def get_default_printer(self):
        if not self.conn:
            return None
        try:
            default_printer = self.conn.getDefault()
            logger.debug(f"Default printer: {default_printer}")
            return default_printer
        except Exception as e:
            logger.error(f"Failed to get default printer: {e}")
            return None

    def set_default_printer(self, printer_name):
        if not self.conn:
            return False
        try:
            self.conn.setDefault(printer_name)
            logger.info(f"Default printer set to '{printer_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to set default printer '{printer_name}': {e}")
            return False

    def discover_devices(self):
        if not self.conn:
            return {}
        logger.debug("Discovering CUPS devices...")
        try:
            devices = self.conn.getDevices()
            logger.debug(f"Discovered {len(devices)} devices.")
            return devices
        except Exception as e:
            logger.error(f"Failed to discover devices: {e}")
            return {}

    def add_printer(self, name, uri, model_name=None, ppd_name=None):
        """
        Adds a printer directly via the CUPS API.
        If no PPD is specified, it automatically finds the most suitable PPD based on the model name.
        """
        if not ppd_name:
            ppd_name = self.find_best_ppd(model_name, device_uri=uri)

        logger.info(f"Attempting to add printer via CUPS API: name='{name}', uri='{uri}', ppd='{ppd_name}'")
        try:
            conn = self.conn if self.conn else cups.Connection()
            conn.addPrinter(name, device=uri, ppdname=ppd_name)
            conn.enablePrinter(name)
            conn.acceptJobs(name)
            logger.info(f"Printer '{name}' added and enabled successfully via CUPS API.")
            return True, None
        except cups.IPPError as e:
            err_msg = f"CUPS IPP Error ({e.args[0]}): {e.args[1]}"
            logger.error(f"Failed to add printer '{name}': {err_msg}")
            return False, err_msg
        except Exception as e:
            err_msg = str(e)
            logger.exception(f"Unexpected error while adding printer '{name}': {err_msg}")
            return False, err_msg

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
            logger.error(f"Failed to get state for printer '{printer_name}': {e}")
            return "unknown"

    def open_queue(self, printer_name):
        try:
            url = f"http://localhost:631/printers/{printer_name}"
            webbrowser.open(url)
            logger.info(f"Opened print queue web page for '{printer_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to open print queue for '{printer_name}': {e}")
            return False

    def get_printer_attributes_by_uri(self, uri):
        """
        Retrieves brand, model, and name attributes from the URI address of a network/IPP printer 
        that has not yet been added, providing data for automatic population.
        """
        # Only query network addresses with IPP / HTTP protocols (exclude cups-pdf:/, cups-brf:/, dnssd://)
        if not uri or not uri.startswith(("ipp://", "ipps://", "http://", "https://")):
            return {}
        
        logger.debug(f"Fetching IPP printer attributes for URI: {uri}")
        try:
            conn = self.conn if self.conn else cups.Connection()
            attrs = conn.getPrinterAttributes(uri=uri)
            
            printer_info = attrs.get('printer-info', '')
            make_and_model = attrs.get('printer-make-and-model', '')
            suggested_name = printer_info if printer_info else make_and_model
            
            return {
                "suggested_name": suggested_name,
                "make_and_model": make_and_model
            }
        except Exception as e:
            logger.debug(f"Could not fetch printer attributes for URI '{uri}': {e}")
            return {}

    @staticmethod
    def get_print_jobs(printer_name: str = None) -> list:
        """Fetch active print jobs from CUPS via lpstat command."""
        jobs = []
        try:
            # lpstat -o command lists open jobs
            cmd = ["lpstat", "-o"]
            if printer_name:
                cmd.append(printer_name)
                
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().split("\n"):
                    # Output format: Printer-123 user size Wed 12 Aug 2026...
                    parts = line.split()
                    if len(parts) >= 3:
                        job_id = parts[0]
                        user = parts[1]
                        size = parts[2]
                        time_str = " ".join(parts[3:]) if len(parts) > 3 else ""
                        jobs.append({
                            "job_id": job_id,
                            "user": user,
                            "size": size,
                            "time": time_str
                        })
        except Exception as e:
            logger.error(f"Failed to fetch print jobs: {e}")
        return jobs

    @staticmethod
    def cancel_print_job(job_id: str) -> bool:
        """Cancel a specific print job by Job ID using cancel command."""
        try:
            res = subprocess.run(["cancel", job_id], capture_output=True, text=True, check=False)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False