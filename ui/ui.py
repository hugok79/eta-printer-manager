import gi
import os
import threading

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.logger import logger
from src.async_loader import AsyncLoader
from src.version import __version__
from src.cups_backend import CupsBackend
from src.queue_window import PrintQueueWindow
from src.notifications import NotificationManager
from src.driver_installer import DynamicDriverInstaller
from src.locale_config import _


def load_css():
    """Loads application CSS stylesheet."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css_path = os.path.join(base_dir, "data", "style.css")
    
    if not os.path.exists(css_path):
        css_path = os.path.abspath(os.path.join("data", "style.css"))
    
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


def get_glade_path():
    """Resolves the path to main_window.glade UI schema file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    glade_path = os.path.join(base_dir, "data", "main_window.glade")
    
    if not os.path.exists(glade_path):
        glade_path = os.path.abspath(os.path.join("data", "main_window.glade"))
    
    if not os.path.exists(glade_path):
        glade_path = "/usr/share/pardus/eta-printer-manager/data/main_window.glade"

    return glade_path


class AddDeviceDialog:
    """Manual Addition + Automatic Network Scanning Dialog (Gtk.Builder)"""
    def __init__(self, parent_window, cups_backend):
        self.cups_backend = cups_backend

        # Load Glade XML interface
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("eta-printer-manager")
        self.builder.add_from_file(get_glade_path())

        self.dialog = self.builder.get_object("add_device_dialog")
        
        parent_widget = parent_window.window if hasattr(parent_window, 'window') else parent_window
        self.dialog.set_transient_for(parent_widget)

        # Retrieve widget references from Builder
        self.entry_name = self.builder.get_object("entry_name")
        self.entry_uri = self.builder.get_object("entry_uri")
        self.combo_driver = self.builder.get_object("combo_driver")
        self.btn_browse_ppd = self.builder.get_object("btn_browse_ppd")
        self.spinner = self.builder.get_object("spinner_discovery")
        self.listbox = self.builder.get_object("listbox_discovered")

        # Standard/General Drivers
        self.combo_driver.append("drv:///sample.drv/generic.ppd", _("Generic PostScript Printer"))
        self.combo_driver.append("drv:///sample.drv/pcl5e.ppd", _("Generic PCL Laser Printer"))
        self.combo_driver.append("everywhere", _("IPP Everywhere (Driverless)"))
        self.combo_driver.append("raw", _("Raw Queue (No Driver)"))
        self.combo_driver.set_active(0)

        # Connect Signals
        self.btn_browse_ppd.connect("clicked", self._on_browse_ppd_clicked)
        self.listbox.connect("row-selected", self._on_device_selected)

        # Start network discovery
        GLib.idle_add(self._start_discovery)

    def _on_browse_ppd_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Select PPD File"),
            parent=self.dialog,
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
        self.spinner.start()

        def scan_worker():
            discovered = []
            try:
                devices = self.cups_backend.discover_devices()
                for uri, info in devices.items():
                    name = info.get('device-make-and-model', info.get('device-info', uri.split('/')[-1]))
                    devclass = info.get('device-class', '')
                    if devclass != 'backend' and name.lower() != 'unknown':
                        discovered.append((name, uri, 'printer'))
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

            self._auto_match_device(row.device_name, row.device_uri)

    def _auto_match_device(self, dev_name, dev_uri):
        """Finds the most suitable PPD in the background."""
        def match_worker():
            attrs = {}
            if hasattr(self.cups_backend, 'get_printer_attributes_by_uri'):
                attrs = self.cups_backend.get_printer_attributes_by_uri(dev_uri)
            
            suggested_name = attrs.get("suggested_name", "")
            make_and_model = attrs.get("make_and_model", "")

            search_query = make_and_model if make_and_model else dev_name
            best_ppd = None
            if hasattr(self.cups_backend, 'find_best_ppd'):
                best_ppd = self.cups_backend.find_best_ppd(search_query)

            GLib.idle_add(self._apply_auto_match, suggested_name, best_ppd)

        threading.Thread(target=match_worker, daemon=True).start()

    def _apply_auto_match(self, suggested_name, best_ppd):
        """Reflects the found PPD and name to the interface."""
        if suggested_name:
            clean_name = suggested_name.replace(" ", "_").replace("-", "_").replace("/", "_")
            self.entry_name.set_text(clean_name)

        if not best_ppd:
            return

        model = self.combo_driver.get_model()

        if model:
            iters_to_remove = []
            it = model.get_iter_first()
            while it:
                label = model.get_value(it, 1)
                if label and "Auto Matched" in label:
                    iters_to_remove.append(it)
                it = model.iter_next(it)
            
            for it in iters_to_remove:
                model.remove(it)

        default_ids = [
            "drv:///sample.drv/generic.ppd",
            "drv:///sample.drv/pcl5e.ppd",
            "everywhere",
            "raw"
        ]

        if best_ppd in default_ids:
            self.combo_driver.set_active_id(best_ppd)
        else:
            display_label = f"★ {best_ppd.split('/')[-1]} (Auto Matched)"
            self.combo_driver.prepend(best_ppd, display_label)
            self.combo_driver.set_active_id(best_ppd)

    def get_result(self):
        active_id = self.combo_driver.get_active_id()
        if not active_id:
            active_id = "drv:///sample.drv/generic.ppd"
        return self.entry_name.get_text().strip(), self.entry_uri.get_text().strip(), active_id

    def connect(self, signal_name, callback):
        self.dialog.connect(signal_name, callback)

    def show_all(self):
        self.dialog.show_all()

    def destroy(self):
        self.dialog.destroy()


class DeviceCard(Gtk.Box):
    """Dynamic Card Widget for Printers and Scanners"""
    def __init__(self, name, device_type, status_text, parent_window, is_default=False, is_paused=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.get_style_context().add_class("device-card")
        self.name = name
        self.device_type = device_type
        self.parent_window = parent_window
        self.is_default = is_default
        self.is_paused = is_paused

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

            btn_pause_label = _("Resume") if is_paused else _("Pause")
            btn_pause = Gtk.Button(label=btn_pause_label)
            btn_pause.get_style_context().add_class("btn-secondary")
            if is_paused:
                btn_pause.connect("clicked", lambda x: self._on_action_clicked(_("Resume Printer"), self._action_resume))
            else:
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
        parent_widget = self.parent_window.window if hasattr(self.parent_window, 'window') else self.parent_window
        dialog = Gtk.MessageDialog(
            transient_for=parent_widget,
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
        win = PrintQueueWindow(printer_name=self.name, parent_window=self.parent_window)
        win.show_all()

    def _action_print_test(self):
        if hasattr(self.parent_window.cups, 'print_test_page'):
            self.parent_window.cups.print_test_page(self.name)

    def _action_set_default(self):
        self.parent_window.cups.set_default_printer(self.name)
        self.parent_window.load_devices()

    def _action_pause(self):
        self.parent_window.cups.pause_printer(self.name)
        self.parent_window.load_devices()

    def _action_resume(self):
        self.parent_window.cups.resume_printer(self.name)
        self.parent_window.load_devices()

    def _action_delete(self):
        if hasattr(self.parent_window.cups, 'delete_printer'):
            if self.parent_window.cups.delete_printer(self.name):
                self.parent_window.load_devices()


class MainWindow:
    """Main Application Window loaded via Gtk.Builder (Glade XML)"""
    def __init__(self, cups_backend=None):
        load_css()

        self.cups = cups_backend if cups_backend else CupsBackend()
        self.notifier = NotificationManager()

        # Load Glade UI with translation domain
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain("eta-printer-manager") 
        self.builder.add_from_file(get_glade_path())

        # Retrieve widget references from Builder
        self.window = self.builder.get_object("main_window")
        self.btn_add_device = self.builder.get_object("btn_add_device")
        self.btn_about = self.builder.get_object("btn_about")
        self.device_list_box = self.builder.get_object("device_list_box")

        # Connect Window & Button Signals
        self.window.connect("destroy", self._on_window_destroy)
        self.btn_add_device.connect("clicked", self._on_add_device_clicked)

        # Connect About Us button signal
        if self.btn_about:
            self.btn_about.connect("clicked", self._on_about_clicked)

        # Auto-refresh: poll CUPS every 1s, only rebuild UI on state change
        self._last_printer_state = None
        self._poll_timer_id = GLib.timeout_add_seconds(1, self._poll_printer_state)
        self._loading = False

        GLib.idle_add(self.load_devices)

    def _on_about_clicked(self, button):
        """Creates and displays native GTK3 About Dialog."""
        about_dialog = Gtk.AboutDialog()
        
        # Configure window modalities
        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)

        # Set application metadata
        about_dialog.set_program_name(_("ETA Printer Manager"))
        about_dialog.set_version(__version__)
        about_dialog.set_comments(_("Printer management tool for ETA and Pardus systems."))
        about_dialog.set_website("https://www.pardus.org.tr")
        about_dialog.set_website_label(_("Pardus Official Website"))
        about_dialog.set_copyright("© TÜBİTAK BİLGEM / Pardus")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        
        # Set developers list
        about_dialog.set_authors([
            "Fatih Altun <dev@pardus.org.tr>",
            "Ali İhsan Özbek <dev@pardus.org.tr>",
            "Pardus Developers <dev@pardus.org.tr>"
        ])

        # Set system icon name
        about_dialog.set_logo_icon_name("eta-printer-manager")

        # Display dialog modally and clean up memory on close
        about_dialog.run()
        about_dialog.destroy()

    def connect(self, signal_name, callback, *args):
        """Proxies connect calls to the underlying GTK Window object."""
        return self.window.connect(signal_name, callback, *args)

    def show_all(self):
        """Shows the window and all child widgets."""
        self.window.show_all()

    def _on_window_destroy(self, widget):
        """Cleans up poll timer on close."""
        if hasattr(self, '_poll_timer_id') and self._poll_timer_id:
            GLib.source_remove(self._poll_timer_id)
            self._poll_timer_id = None
        Gtk.main_quit()

    def _build_printer_state_key(self, printers, default_printer):
        """Builds a hashable snapshot of all printer names, states, and the default."""
        if not isinstance(printers, dict):
            return None
        parts = []
        for name in sorted(printers.keys()):
            attrs = printers[name]
            state = attrs.get('printer-state', 0)
            parts.append(f"{name}:{state}")
        parts.append(f"default:{default_printer}")
        return "|".join(parts)

    def _poll_printer_state(self):
        """Fetches printers in background, rebuilds UI only if state actually changed."""
        if self._loading:
            return True
        self._loading = True
        AsyncLoader.run_async(
            task_func=self._fetch_devices,
            callback=self._on_poll_result
        )
        return True

    def _on_poll_result(self, result, error):
        """Callback for poll. Skips rebuild if state unchanged."""
        self._loading = False
        if error or not result:
            return
        printers, default_printer = result
        key = self._build_printer_state_key(printers, default_printer)
        if key == self._last_printer_state:
            return
        self._last_printer_state = key
        self._rebuild_device_list(printers, default_printer)

    def show_error_dialog(self, title, message):
        """Shows error dialog to the user."""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
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
        add_dialog = AddDeviceDialog(self, self.cups)

        # Parent pencereyi güvenli şekilde çözelim (Gtk.Window türevi nesneye ulaşıyoruz)
        parent_win = add_dialog if isinstance(add_dialog, Gtk.Window) else getattr(
            add_dialog, 'dialog', getattr(add_dialog, 'window', getattr(self, 'window', None))
        )

        def on_response(gtk_dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                name, uri, ppd = add_dialog.get_result()
                
                name = name.strip() if name else ""
                uri = uri.strip() if uri else ""

                # --- FORM VALIDATION ---
                # 1. Empty field check
                if not name or not uri:
                    dialog = Gtk.MessageDialog(
                        transient_for=parent_win,
                        flags=Gtk.DialogFlags.MODAL,
                        message_type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text=_("Missing Information")
                    )
                    dialog.format_secondary_text(
                        _("Please fill in both Device Name and Connection Address (URI).")
                    )
                    dialog.run()
                    dialog.destroy()
                    return

                # 2. Space check
                if " " in name:
                    dialog = Gtk.MessageDialog(
                        transient_for=parent_win,
                        flags=Gtk.DialogFlags.MODAL,
                        message_type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text=_("Invalid Device Name")
                    )
                    dialog.format_secondary_text(
                        _("Device name cannot contain spaces. Please use underscores (_) or join words.")
                    )
                    dialog.run()
                    dialog.destroy()
                    return

                # 1. Main Thread: Check and prompt for missing driver package
                if not DynamicDriverInstaller.check_and_install_driver(add_dialog, name):
                    logger.info("Driver installation cancelled or failed. Aborting printer creation.")
                    add_dialog.destroy()
                    button.set_sensitive(True)
                    return
            
                # 2. Worker Thread: Add printer via CUPS backend
                def add_task():
                    result = (False, _("Backend error"))
                    if getattr(self.cups, 'add_printer', None):
                        result = self.cups.add_printer(name, uri, ppd_name=ppd)
                    GLib.idle_add(self._on_printer_added, result)

                threading.Thread(target=add_task, daemon=True).start()

            add_dialog.destroy()
            button.set_sensitive(True)

        add_dialog.connect("response", on_response)
        add_dialog.show_all()
        
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
        """Clears list and fetches devices in background. Skips if a fetch is already in-flight."""
        if self._loading:
            return GLib.SOURCE_REMOVE
        self._loading = True

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
        default_printer = self.cups.get_default_printer()
        return printers, default_printer

    def _rebuild_device_list(self, printers, default_printer):
        """Clears and rebuilds the device card list from printer data."""
        for child in self.device_list_box.get_children():
            self.device_list_box.remove(child)
            child.destroy()

        if isinstance(printers, dict):
            for name, attrs in printers.items():
                is_default = (name == default_printer)
                status = CupsBackend.get_printer_status_from_attrs(attrs)
                is_paused = (status == 'stopped')
                if is_default:
                    status_text = _("Default Printer")
                elif is_paused:
                    status_text = _("Paused")
                else:
                    status_text = _("Idle")
                card = DeviceCard(name, "printer", status_text, self, is_default=is_default, is_paused=is_paused)
                self.device_list_box.pack_start(card, False, False, 0)

        self.device_list_box.show_all()

    def _on_devices_loaded(self, result, error):
        """Callback for manual load_devices(). Always rebuilds."""
        self._loading = False
        if error:
            logger.error(f"Error loading devices: {error}")
            return
        printers, default_printer = result
        self._last_printer_state = self._build_printer_state_key(printers, default_printer)
        self._rebuild_device_list(printers, default_printer)