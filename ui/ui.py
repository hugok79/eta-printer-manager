import gi
import os
import threading
import json
import subprocess
import sys
import cups

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.logger import logger
from src.async_loader import AsyncLoader
from src.cups_backend import CupsBackend
from src.scanner_backend import ScannerBackend
from src.notifications import NotificationManager
from src.locale_config import _


def load_css():
    # Priority 1: The local style.css file in the project's own folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css_path = os.path.join(base_dir, "data", "style.css")
    
    if not os.path.exists(css_path):
        css_path = os.path.abspath(os.path.join("data", "style.css"))
    
    # Priority 2: If not present in the project, use the file installed in the system (Fallback)
    if not os.path.exists(css_path):
        css_path = "/usr/share/pardus/eta-printer-manager/data/style.css"

    if os.path.exists(css_path):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )


class AddDeviceDialog(Gtk.Dialog):
    """Manual Addition + Automatic Network Scanning Dialog"""
    def __init__(self, parent, cups_backend, scanner_backend):
        super().__init__(title=_("Add Device"), transient_for=parent)
        self.cups_backend = cups_backend
        self.scanner_backend = scanner_backend
        self.set_modal(True)
        self.set_default_size(540, 520)

        # Bottom Buttons
        self.btn_cancel = self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.btn_cancel.get_style_context().add_class("btn-secondary")

        self.btn_add = self.add_button(_("Add"), Gtk.ResponseType.OK)
        self.btn_add.get_style_context().add_class("btn-primary")

        content_area = self.get_content_area()
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox_main.set_border_width(18)
        content_area.add(vbox_main)

        # ─── SECTION 1: Manual Device Addition ───
        lbl_manual = Gtk.Label(label=_("Add Device Manually"), xalign=0)
        lbl_manual.get_style_context().add_class("card-title")
        vbox_main.pack_start(lbl_manual, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        lbl_name = Gtk.Label(label=_("Device Name:"), xalign=0)
        lbl_name.get_style_context().add_class("card-subtitle")
        self.entry_name = Gtk.Entry()
        self.entry_name.set_placeholder_text(_("e.g. Office_Printer"))

        lbl_uri = Gtk.Label(label=_("Connection Address (URI):"), xalign=0)
        lbl_uri.get_style_context().add_class("card-subtitle")
        self.entry_uri = Gtk.Entry()
        self.entry_uri.set_placeholder_text(_("e.g. ipp://192.168.1.50/ipp/print"))

        lbl_driver = Gtk.Label(label=_("Driver (PPD):"), xalign=0)
        lbl_driver.get_style_context().add_class("card-subtitle")
        
        hbox_driver = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.combo_driver = Gtk.ComboBoxText()
        
        # Standard/General Drivers (No disk scan is performed)
        self.combo_driver.append("drv:///sample.drv/generic.ppd", _("Generic PostScript Printer"))
        self.combo_driver.append("drv:///sample.drv/pcl5e.ppd", _("Generic PCL Laser Printer"))
        self.combo_driver.append("everywhere", _("IPP Everywhere (Driverless)"))
        self.combo_driver.append("raw", _("Raw Queue (No Driver)"))
        self.combo_driver.set_active(0)

        btn_browse_ppd = Gtk.Button(label=_("Browse PPD..."))
        btn_browse_ppd.get_style_context().add_class("btn-secondary")
        btn_browse_ppd.connect("clicked", self._on_browse_ppd_clicked)

        hbox_driver.pack_start(self.combo_driver, True, True, 0)
        hbox_driver.pack_start(btn_browse_ppd, False, False, 0)

        grid.attach(lbl_name, 0, 0, 1, 1)
        grid.attach(self.entry_name, 1, 0, 1, 1)
        grid.attach(lbl_uri, 0, 1, 1, 1)
        grid.attach(self.entry_uri, 1, 1, 1, 1)
        grid.attach(lbl_driver, 0, 2, 1, 1)
        grid.attach(hbox_driver, 1, 2, 1, 1)

        self.entry_name.set_hexpand(True)
        self.entry_uri.set_hexpand(True)
        hbox_driver.set_hexpand(True)
        vbox_main.pack_start(grid, False, False, 0)

        # Separator
        vbox_main.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        # ─── SECTION 2: Network & System Discovered Devices ───
        hbox_auto_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_auto = Gtk.Label(label=_("Devices Found on Network and System"), xalign=0)
        lbl_auto.get_style_context().add_class("card-title")
        hbox_auto_header.pack_start(lbl_auto, True, True, 0)

        self.spinner = Gtk.Spinner()
        hbox_auto_header.pack_end(self.spinner, False, False, 0)
        vbox_main.pack_start(hbox_auto_header, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(180)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_device_selected)
        scroll.add(self.listbox)
        vbox_main.pack_start(scroll, True, True, 0)

        # Fast network scan starts only
        GLib.idle_add(self._start_discovery)

    def _on_browse_ppd_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Select PPD File"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            _("Cancel"), Gtk.ResponseType.CANCEL,
            _("Open"), Gtk.ResponseType.OK
        )
        filter_ppd = Gtk.FileFilter()
        filter_ppd.set_name(_("PPD Files (*.ppd, *.ppd.gz)"))
        filter_ppd.add_pattern("*.ppd")
        filter_ppd.add_pattern("*.ppd.gz")
        dialog.add_filter(filter_ppd)

        if dialog.run() == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if filepath:
                self.combo_driver.append(filepath, os.path.basename(filepath))
                self.combo_driver.set_active_id(filepath)
        dialog.destroy()

    def _start_discovery(self):
        """Network and system printers are scanned"""
        self.spinner.start()

        def scan_worker():
            discovered = []
            py_script = (
                "import cups, json\n"
                "devs = []\n"
                "try:\n"
                "    conn = cups.Connection()\n"
                "    cups_devs = conn.getDevices(timeout=5)\n"
                "    for uri, info in cups_devs.items():\n"
                "        name = info.get('device-make-and-model', info.get('device-info', uri.split('/')[-1]))\n"
                "        devclass = info.get('device-class', '')\n"
                "        if devclass != 'backend' and name.lower() != 'unknown':\n"
                "            devs.append((name, uri, 'printer'))\n"
                "except Exception:\n"
                "    pass\n"
                "print(json.dumps(devs))\n"
            )
            try:
                # Timeout increased to 8 seconds to allow network packet collection
                out = subprocess.check_output(
                    [sys.executable, "-c", py_script],
                    text=True,
                    timeout=8,
                    stderr=subprocess.DEVNULL
                )
                discovered = json.loads(out)
            except Exception:
                pass

            GLib.idle_add(self._on_discovery_finished, discovered)

        threading.Thread(target=scan_worker, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def _on_discovery_finished(self, discovered_devices):
        self.spinner.stop()
        self.spinner.hide()

        if not discovered_devices:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=_("No automatic devices found. Please add manually above."), xalign=0)
            lbl.get_style_context().add_class("card-subtitle")
            lbl.set_margin_top(10)
            lbl.set_margin_bottom(10)
            lbl.set_margin_left(10)
            row.add(lbl)
            row.set_selectable(False)
            self.listbox.add(row)
        else:
            for name, uri, dev_type in discovered_devices:
                if dev_type != "printer":
                    continue

                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                hbox.set_margin_top(8)
                hbox.set_margin_bottom(8)
                hbox.set_margin_left(10)
                hbox.set_margin_right(10)

                icon_name = "printer-symbolic"
                img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
                img.get_style_context().add_class("blue-icon")
                hbox.pack_start(img, False, False, 0)

                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                lbl_n = Gtk.Label(label=name, xalign=0)
                lbl_n.get_style_context().add_class("card-title")
                lbl_u = Gtk.Label(label=uri, xalign=0)
                lbl_u.get_style_context().add_class("card-subtitle")

                vbox.pack_start(lbl_n, False, False, 0)
                vbox.pack_start(lbl_u, False, False, 0)
                hbox.pack_start(vbox, True, True, 0)

                row.add(hbox)
                row.device_name = name
                row.device_uri = uri
                self.listbox.add(row)

        self.listbox.show_all()
        return GLib.SOURCE_REMOVE

    def _on_device_selected(self, listbox, row):
        if row and hasattr(row, 'device_uri'):
            clean_name = row.device_name.replace(" ", "_").replace("-", "_").replace("/", "_")
            self.entry_name.set_text(clean_name)
            self.entry_uri.set_text(row.device_uri)

            # Auto IPP Information Fetching and Best PPD Matching
            self._auto_match_device(row.device_name, row.device_uri)

    def _auto_match_device(self, dev_name, dev_uri):
        """When a network device is selected, it finds the most suitable PPD in the background and retrieves information."""
        def match_worker():
            # Query IPP Attributes from Backend
            attrs = {}
            if hasattr(self.cups_backend, 'get_printer_attributes_by_uri'):
                attrs = self.cups_backend.get_printer_attributes_by_uri(dev_uri)
            
            suggested_name = attrs.get("suggested_name", "")
            make_and_model = attrs.get("make_and_model", "")

            # Search for the most suitable PPD in the system according to the model information
            search_query = make_and_model if make_and_model else dev_name
            best_ppd = None
            if hasattr(self.cups_backend, 'find_best_ppd'):
                best_ppd = self.cups_backend.find_best_ppd(search_query)

            # Update the User Interface on the Main Thread
            GLib.idle_add(self._apply_auto_match, suggested_name, best_ppd)

        threading.Thread(target=match_worker, daemon=True).start()

    def _apply_auto_match(self, suggested_name, best_ppd):
        """Reflects the found PPD and name to the interface boxes."""
        if suggested_name:
            clean_name = suggested_name.replace(" ", "_").replace("-", "_").replace("/", "_")
            self.entry_name.set_text(clean_name)

        if not best_ppd:
            return

        model = self.combo_driver.get_model()

        # Remove all previously added "Auto Matched" (★) entries from the menu
        if model:
            iters_to_remove = []
            it = model.get_iter_first()
            while it:
                label = model.get_value(it, 1) # Column 1 is the display name
                if label and "Auto Matched" in label:
                    iters_to_remove.append(it)
                it = model.iter_next(it)
            
            for it in iters_to_remove:
                model.remove(it)

        # If the found PPD is one of the default generic drivers, select it directly from the list (Do not add a new star!)
        default_ids = [
            "drv:///sample.drv/generic.ppd",
            "drv:///sample.drv/pcl5e.ppd",
            "everywhere",
            "raw"
        ]

        if best_ppd in default_ids:
            self.combo_driver.set_active_id(best_ppd)
        else:
            # Only add and select the REAL system-specific PPD with a star at the top
            display_label = f"★ {best_ppd.split('/')[-1]} (Auto Matched)"
            self.combo_driver.prepend(best_ppd, display_label)
            self.combo_driver.set_active_id(best_ppd)

    def get_result(self):
        active_id = self.combo_driver.get_active_id()
        if not active_id:
            active_id = "drv:///sample.drv/generic.ppd"
        return self.entry_name.get_text().strip(), self.entry_uri.get_text().strip(), active_id


class DeviceCard(Gtk.Box):
    def __init__(self, name, device_type, status_text, parent_window, is_default=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        

        self.get_style_context().add_class("device-card")
        self.name = name
        self.device_type = device_type
        self.parent_window = parent_window
        self.is_default = is_default

        self.set_margin_left(6)
        self.set_margin_right(6)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        # Header Row
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        icon_name = "printer-symbolic" if device_type == "printer" else "camera-web-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
        icon.get_style_context().add_class("blue-icon")
        header_box.pack_start(icon, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label=name, xalign=0)
        title_lbl.get_style_context().add_class("card-title")

        type_str = _("Printer") if device_type == "printer" else _("Scanner")
        sub_lbl = Gtk.Label(label=f"{type_str} · {status_text}", xalign=0)
        sub_lbl.get_style_context().add_class("card-subtitle")

        text_box.pack_start(title_lbl, False, False, 0)
        text_box.pack_start(sub_lbl, False, False, 0)
        header_box.pack_start(text_box, True, True, 0)

        self.arrow_icon = Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON)
        header_box.pack_end(self.arrow_icon, False, False, 0)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(8)

        if device_type == "printer":
            btn_queue = Gtk.Button(label=_("Open Queue"))
            btn_queue.get_style_context().add_class("btn-secondary")
            btn_queue.connect("clicked", lambda x: self._on_action_clicked(_("Open Queue"), self._action_open_queue))

            btn_test = Gtk.Button(label=_("Test Page"))
            btn_test.get_style_context().add_class("btn-secondary")
            btn_test.connect("clicked", lambda x: self._on_action_clicked(_("Send Test Page"), self._action_print_test))

            btn_default_label = _("Default") if is_default else _("Set as Default")
            btn_default = Gtk.Button(label=btn_default_label)
            btn_default.get_style_context().add_class("btn-secondary")
            if is_default:
                btn_default.set_sensitive(False)
            else:
                btn_default.connect("clicked", lambda x: self._on_action_clicked(_("Set as Default Printer"), self._action_set_default))

            btn_pause = Gtk.Button(label=_("Pause"))
            btn_pause.get_style_context().add_class("btn-secondary")
            btn_pause.connect("clicked", lambda x: self._on_action_clicked(_("Pause Printer"), self._action_pause))

            btn_delete = Gtk.Button(label=_("Remove"))
            btn_delete.get_style_context().add_class("btn-danger")
            btn_delete.connect("clicked", lambda x: self._on_action_clicked(_("Remove Printer"), self._action_delete))

            action_box.pack_start(btn_queue, False, False, 0)
            action_box.pack_start(btn_test, False, False, 0)
            action_box.pack_start(btn_default, False, False, 0)
            action_box.pack_start(btn_pause, False, False, 0)
            action_box.pack_start(btn_delete, False, False, 0)

        self.revealer.add(action_box)

        header_event_box = Gtk.EventBox()
        header_event_box.add(header_box)
        header_event_box.connect("button-press-event", self.toggle_reveal)

        self.pack_start(header_event_box, False, False, 0)
        self.pack_start(self.revealer, False, False, 0)

    def toggle_reveal(self, widget, event):
        is_revealed = self.revealer.get_reveal_child()
        self.revealer.set_reveal_child(not is_revealed)
        icon_name = "pan-up-symbolic" if not is_revealed else "pan-down-symbolic"
        self.arrow_icon.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

    def _confirm_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.set_default_response(Gtk.ResponseType.OK)

        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _on_action_clicked(self, action_name, callback):
        msg = _("Do you want to perform '{1}' action for device '{0}'?").format(self.name, action_name)
        if self._confirm_dialog(action_name, msg):
            callback()

    def _action_open_queue(self):
        self.parent_window.cups.open_queue(self.name)

    def _action_print_test(self):
        if hasattr(self.parent_window.cups, 'print_test_page'):
            self.parent_window.cups.print_test_page(self.name)

    def _action_set_default(self):
        try:
            conn = cups.Connection()
            conn.setDefault(self.name)
        except Exception:
            if hasattr(self.parent_window.cups, 'set_default_printer'):
                self.parent_window.cups.set_default_printer(self.name)

        self.parent_window.load_devices()

    def _action_pause(self):
        self.parent_window.cups.pause_printer(self.name)

    def _action_delete(self):
        if hasattr(self.parent_window.cups, 'delete_printer'):
            if self.parent_window.cups.delete_printer(self.name):
                self.parent_window.load_devices()


class MainWindow(Gtk.Window):
    def __init__(self, cups_backend=None, scanner_backend=None):
        super().__init__(title=_("Printers and Scanners"))
        self.set_default_size(750, 600)
        load_css()

        self.cups = cups_backend if cups_backend else CupsBackend()
        self.scanner = scanner_backend if scanner_backend else ScannerBackend()
        self.notifier = NotificationManager()

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(_("Printers and Scanners"))
        self.set_titlebar(header)

        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.btn_refresh.get_style_context().add_class("top-icon-btn")
        self.btn_refresh.connect("clicked", lambda x: self.load_devices())

        header.pack_end(self.btn_refresh)

        scroll = Gtk.ScrolledWindow()
        self.add(scroll)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)

        scroll.add(main_box)

        lbl_main = Gtk.Label(label=_("Printers and Scanners"), xalign=0)
        lbl_main.get_style_context().add_class("main-title")
        lbl_main.set_margin_left(12)
        main_box.pack_start(lbl_main, False, False, 0)

        add_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        add_card.get_style_context().add_class("add-device-card")
        add_card.set_margin_left(6)
        add_card.set_margin_right(6)

        add_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_title = Gtk.Label(label=_("Add Device"), xalign=0)
        add_title.get_style_context().add_class("card-title")
        add_sub = Gtk.Label(label=_("Add a printer or scanner on network or USB"), xalign=0)
        add_sub.get_style_context().add_class("card-subtitle")

        add_text_box.pack_start(add_title, False, False, 0)
        add_text_box.pack_start(add_sub, False, False, 0)
        add_card.pack_start(add_text_box, True, True, 0)

        btn_add_device = Gtk.Button(label=_("Add Device"))
        btn_add_device.get_style_context().add_class("btn-primary")
        btn_add_device.connect("clicked", self._on_add_device_clicked)
        add_card.pack_end(btn_add_device, False, False, 0)

        main_box.pack_start(add_card, False, False, 0)

        lbl_section = Gtk.Label(label=_("Your Devices"), xalign=0)
        lbl_section.get_style_context().add_class("section-title")
        lbl_section.set_margin_left(12)
        main_box.pack_start(lbl_section, False, False, 0)

        self.device_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.pack_start(self.device_list_box, True, True, 0)

        GLib.idle_add(self.load_devices)

    def show_error_dialog(self, title, message):
        """Shows a detailed error notification window to the user."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _on_add_device_clicked(self, button):
        button.set_sensitive(False)
        dialog = AddDeviceDialog(self, self.cups, self.scanner)

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK:
                name, uri, ppd = dlg.get_result()
                if name and uri:
                    def add_task():
                        result = (False, _("Backend error"))
                        if getattr(self.cups, 'add_printer', None):
                            result = self.cups.add_printer(name, uri, ppd_name=ppd)
                        GLib.idle_add(self._on_printer_added, result)

                    threading.Thread(target=add_task, daemon=True).start()

            dlg.destroy()
            button.set_sensitive(True)

        dialog.connect("response", on_response)
        dialog.show_all()

    def _on_printer_added(self, result):
        if isinstance(result, tuple):
            success, error_msg = result
        else:
            success, error_msg = result, None

        if success:
            logger.info("Printer added successfully, refreshing device list.")
            self.notifier.notify(_("Success"), _("Device added successfully."))
            self.load_devices()
        else:
            logger.error(f"Printer addition failed: {error_msg}")
            self.show_error_dialog(
                _("Failed to Add Device"),
                _("An error occurred while adding the printer:\n\n{0}").format(error_msg or _("Unknown error"))
            )
        return GLib.SOURCE_REMOVE

    def load_devices(self):
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.set_sensitive(False)

        for child in self.device_list_box.get_children():
            self.device_list_box.remove(child)
            child.destroy()

        AsyncLoader.run_async(
            task_func=self._fetch_devices,
            callback=self._on_devices_loaded
        )
        return GLib.SOURCE_REMOVE

    def _fetch_devices(self):
        printers = self.cups.get_printers()
        default_printer = None

        try:
            conn = cups.Connection()
            default_printer = conn.getDefault()
        except Exception:
            if hasattr(self.cups, 'get_default_printer'):
                default_printer = self.cups.get_default_printer()

        return printers, {}, default_printer

    def _on_devices_loaded(self, result, error):
        # Button re-enable time delay (cooldown) is set to 5 seconds
        if hasattr(self, 'btn_refresh'):
            def reenable_refresh():
                if hasattr(self, 'btn_refresh') and self.btn_refresh:
                    self.btn_refresh.set_sensitive(True)
                    logger.debug("Refresh button re-enabled after 5 seconds cooldown.")
                return False  # GLib timer closes after one run

            # Run reenable_refresh function after 5 seconds
            GLib.timeout_add_seconds(5, reenable_refresh)

        if error:
            logger.error(f"Error loading devices: {error}")
            return

        printers, scanners, default_printer = result

        if isinstance(printers, dict):
            for name in printers.keys():
                is_default = (name == default_printer)
                status_text = _("Default Printer") if is_default else _("Idle")
                card = DeviceCard(name, "printer", status_text, self, is_default=is_default)
                self.device_list_box.pack_start(card, False, False, 0)

        self.device_list_box.show_all()