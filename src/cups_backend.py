# pyrefly: ignore [missing-import]
import cups
import webbrowser
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
        if not self.conn:
            return {}
        logger.debug("Fetching printer list from CUPS...")
        try:
            printers = self.conn.getPrinters()
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
        if not self.conn:
            return {}
        logger.debug("Fetching PPD list from CUPS...")
        try:
            ppds = self.conn.getPPDs()
            logger.debug(f"Found {len(ppds)} PPD drivers.")
            return ppds
        except Exception as e:
            logger.error(f"Failed to fetch PPD drivers: {e}")
            return {}

    def find_best_ppd(self, model_name):
        """
        Scans the system for PPDs based on the 'ppd-make-and-model' field.
        If a match is found, it returns that PPD; otherwise, it returns the default Generic PostScript PPD.
        """
        default_ppd = "drv:///sample.drv/generic.ppd"
        if not model_name:
            return default_ppd

        ppds = self.get_ppds()
        target = model_name.strip().lower()

        # 1. Exact match check
        for ppd_key, ppd_info in ppds.items():
            make_model = ppd_info.get("ppd-make-and-model", "").strip().lower()
            if make_model == target:
                logger.info(f"Exact PPD match found for '{model_name}': {ppd_key}")
                return ppd_key

        # 2. Partial (inclusion) match check
        for ppd_key, ppd_info in ppds.items():
            make_model = ppd_info.get("ppd-make-and-model", "").strip().lower()
            if target in make_model or make_model in target:
                logger.info(f"Partial PPD match found for '{model_name}': {ppd_key}")
                return ppd_key

        logger.info(f"No matching PPD found for '{model_name}'. Falling back to Generic PostScript.")
        return default_ppd

    def print_test_page(self, printer_name):
        if not self.conn:
            return False
        test_file_path = "/tmp/pardus_test_page.txt"
        try:
            with open(test_file_path, "w") as f:
                f.write("Pardus Printer Test Page\n\nIf this page prints successfully, your printer is working correctly.\n")
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
            ppd_name = self.find_best_ppd(model_name)

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