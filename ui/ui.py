import gi
import os
import threading
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from src.async_loader import AsyncLoader
from src.cups_backend import CupsBackend
from src.scanner_backend import ScannerBackend
from src.notifications import NotificationManager
from src.locale_config import _ 

def load_css():
    css_provider = Gtk.CssProvider()
    css_path = "/usr/share/pardus/eta-printer-manager/data/style.css"
    if not os.path.exists(css_path):
        css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "style.css")
        if not os.path.exists(css_path):
            css_path = os.path.abspath(os.path.join("data", "style.css"))
        
    if os.path.exists(css_path):
        css_provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


class AddDeviceDialog(Gtk.Dialog):
    """Windows 11 Tarzı Manuel Ekleme + Otomatik Ağ Taraması Diyaloğu"""
    def __init__(self, parent, cups_backend, scanner_backend):
        super().__init__(title=_("Cihaz Ekle"), transient_for=parent, flags=0)
        self.cups_backend = cups_backend
        self.scanner_backend = scanner_backend

        self.set_default_size(520, 540)
        
        # Alt Butonlar
        self.btn_cancel = self.add_button(_("İptal"), Gtk.ResponseType.CANCEL)
        self.btn_cancel.get_style_context().add_class("btn-secondary")
        
        self.btn_add = self.add_button(_("Ekle"), Gtk.ResponseType.OK)
        self.btn_add.get_style_context().add_class("btn-primary")

        content_area = self.get_content_area()
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox_main.set_border_width(18)
        content_area.add(vbox_main)

        # ─── 1. BÖLÜM: Manuel Cihaz Ekleme ───
        lbl_manual = Gtk.Label(label=_("Manuel Cihaz Ekle"), xalign=0)
        lbl_manual.get_style_context().add_class("card-title")
        vbox_main.pack_start(lbl_manual, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        lbl_name = Gtk.Label(label=_("Cihaz Adı:"), xalign=0)
        lbl_name.get_style_context().add_class("card-subtitle")
        self.entry_name = Gtk.Entry()
        self.entry_name.set_placeholder_text(_("Örn: Ofis_Yazicisi"))

        lbl_uri = Gtk.Label(label=_("Bağlantı Adresi (URI):"), xalign=0)
        lbl_uri.get_style_context().add_class("card-subtitle")
        self.entry_uri = Gtk.Entry()
        self.entry_uri.set_placeholder_text(_("Örn: ipp://192.168.1.50/ipp/print"))

        grid.attach(lbl_name, 0, 0, 1, 1)
        grid.attach(self.entry_name, 1, 0, 1, 1)
        grid.attach(lbl_uri, 0, 1, 1, 1)
        grid.attach(self.entry_uri, 1, 1, 1, 1)
        
        self.entry_name.set_hexpand(True)
        self.entry_uri.set_hexpand(True)
        vbox_main.pack_start(grid, False, False, 0)

        # Seperatör
        vbox_main.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        # ─── 2. BÖLÜM: Ağda/Sistemde Bulunan Cihazlar ───
        hbox_auto_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_auto = Gtk.Label(label=_("Ağda ve Sistemde Bulunan Cihazlar"), xalign=0)
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

        vbox_main.show_all()
        self._start_discovery()

    
    def _start_discovery(self):
        """Ağ taramasını arka planda başlatır ve protokol çöplerini filtreler"""
        self.spinner.start()
        
        def scan_worker():
            discovered = []
            # Filtrelenecek sahte protokol isimleri ve tanımsız kelimeler
            IGNORE_KEYWORDS = {"unknown", "lpd", "https", "ipps", "ipp", "http", "socket", "smb", "snmp", "dnssd"}

            # 1. CUPS / Ağ Taraması
            try:
                get_devs = getattr(self.cups_backend, 'get_devices', None) or getattr(self.cups_backend, 'discover_devices', None)
                if callable(get_devs):
                    cups_devs = get_devs()
                    if isinstance(cups_devs, dict):
                        for uri, info in cups_devs.items():
                            if not isinstance(info, dict):
                                continue

                            dev_class = info.get('device-class', '').strip()
                            make_model = info.get('device-make-and-model', '').strip()
                            dev_info = info.get('device-info', '').strip()

                            # CUPS protokol backend'lerini ve 'Unknown' cihazları atla
                            if dev_class == "backend" or make_model.lower() == "unknown":
                                continue

                            # İsim belirleme (Model yoksa genel cihaz bilgisini al)
                            name = make_model or dev_info or uri.split('/')[-1]

                            # İsmi veya URI'si protokol çöplerinden biriyse ekleme
                            if name.lower() in IGNORE_KEYWORDS or uri.lower() in IGNORE_KEYWORDS:
                                continue

                            discovered.append((name, uri, "printer"))
            except Exception:
                pass

            # 2. SANE / Tarayıcı Taraması
            try:
                scanners = self.scanner_backend.get_scanners()
                if isinstance(scanners, dict):
                    for dev_id, info in scanners.items():
                        desc = info.get('description', dev_id) if isinstance(info, dict) else str(dev_id)
                        if desc.lower() not in IGNORE_KEYWORDS and str(dev_id).lower() not in IGNORE_KEYWORDS:
                            discovered.append((desc, dev_id, "scanner"))
                elif isinstance(scanners, list):
                    for sc in scanners:
                        if isinstance(sc, dict):
                            desc = sc.get('description', sc.get('name', 'Scanner'))
                            sc_uri = sc.get('uri', '')
                            if desc.lower() not in IGNORE_KEYWORDS:
                                discovered.append((desc, sc_uri, "scanner"))
            except Exception:
                pass

            GLib.idle_add(self._on_discovery_finished, discovered)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _on_discovery_finished(self, discovered_devices):
        self.spinner.stop()
        self.spinner.hide()

        if not discovered_devices:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=_("Otomatik cihaz bulunamadı. Lütfen yukarıdan manuel ekleyin."), xalign=0)
            lbl.get_style_context().add_class("card-subtitle")
            lbl.set_margin_top(10)
            lbl.set_margin_bottom(10)
            lbl.set_margin_left(10)
            row.add(lbl)
            row.set_selectable(False)
            self.listbox.add(row)
        else:
            for name, uri, dev_type in discovered_devices:
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                hbox.set_margin_top(8)
                hbox.set_margin_bottom(8)
                hbox.set_margin_left(10)
                hbox.set_margin_right(10)

                icon_name = "printer-symbolic" if dev_type == "printer" else "camera-web-symbolic"
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

    def _on_device_selected(self, listbox, row):
        """Listeden seçilen cihazın bilgilerini üstteki form alanlarına doldurur"""
        if row and hasattr(row, 'device_uri'):
            clean_name = row.device_name.replace(" ", "_").replace("-", "_")
            self.entry_name.set_text(clean_name)
            self.entry_uri.set_text(row.device_uri)

    def get_result(self):
        return self.entry_name.get_text(), self.entry_uri.get_text()


class DeviceCard(Gtk.Box):
    def __init__(self, name, device_type, status_text, parent_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_style_context().add_class("device-card")
        self.name = name
        self.device_type = device_type
        self.parent_window = parent_window

        # ─── KENAR BOŞLUKLARI (6px İçeri Alma) ───
        self.set_margin_left(6)
        self.set_margin_right(6)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        # Üst Başlık Satırı
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Simge (Mavi)
        icon_name = "printer-symbolic" if device_type == "printer" else "camera-web-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
        icon.get_style_context().add_class("blue-icon")
        header_box.pack_start(icon, False, False, 0)

        # İsim ve Durum Metinleri
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label=name, xalign=0)
        title_lbl.get_style_context().add_class("card-title")
        
        type_str = _("Yazıcı") if device_type == "printer" else _("Tarayıcı")
        sub_lbl = Gtk.Label(label=f"{type_str} · {status_text}", xalign=0)
        sub_lbl.get_style_context().add_class("card-subtitle")

        text_box.pack_start(title_lbl, False, False, 0)
        text_box.pack_start(sub_lbl, False, False, 0)
        header_box.pack_start(text_box, True, True, 0)

        # Açılır/Kapanır Ok Simgesi
        self.arrow_icon = Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON)
        header_box.pack_end(self.arrow_icon, False, False, 0)

        # Genişletilebilir Detay Bölümü (Revealer)
        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(8)

        if device_type == "printer":
            # 1. Kuyruğu Aç Butonu
            btn_queue = Gtk.Button(label=_("Kuyruğu Aç"))
            btn_queue.get_style_context().add_class("btn-secondary")
            btn_queue.connect("clicked", lambda x: self._on_action_clicked(_("Kuyruğu Aç"), self._action_open_queue))
            
            # 2. Sınama Sayfası Butonu
            btn_test = Gtk.Button(label=_("Sınama Sayfası"))
            btn_test.get_style_context().add_class("btn-secondary")
            btn_test.connect("clicked", lambda x: self._on_action_clicked(_("Sınama Sayfası Gönder"), self._action_print_test))

            # 3. Varsayılan Yap Butonu
            btn_default = Gtk.Button(label=_("Varsayılan Yap"))
            btn_default.get_style_context().add_class("btn-secondary")
            btn_default.connect("clicked", lambda x: self._on_action_clicked(_("Varsayılan Yazıcı Yap"), self._action_set_default))

            # 4. Duraklat Butonu
            btn_pause = Gtk.Button(label=_("Duraklat"))
            btn_pause.get_style_context().add_class("btn-secondary")
            btn_pause.connect("clicked", lambda x: self._on_action_clicked(_("Yazıcıyı Duraklat"), self._action_pause))

            # 5. Kaldır (Sil) Butonu
            btn_delete = Gtk.Button(label=_("Kaldır"))
            btn_delete.get_style_context().add_class("btn-danger")
            btn_delete.connect("clicked", lambda x: self._on_action_clicked(_("Yazıcıyı Kaldır"), self._action_delete))

            action_box.pack_start(btn_queue, False, False, 0)
            action_box.pack_start(btn_test, False, False, 0)
            action_box.pack_start(btn_default, False, False, 0)
            action_box.pack_start(btn_pause, False, False, 0)
            action_box.pack_start(btn_delete, False, False, 0)

        self.revealer.add(action_box)

        # Tıklanabilir Alan
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
    def toggle_reveal(self, widget, event):
        is_revealed = self.revealer.get_reveal_child()
        self.revealer.set_reveal_child(not is_revealed)
        icon_name = "pan-up-symbolic" if not is_revealed else "pan-down-symbolic"
        self.arrow_icon.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

    # ─── ONAY DİYALOĞU MEKANİZMASI ───
    def _confirm_dialog(self, title, message):
        """Kullanıcıya 'Devam etmek istiyor musunuz?' sorusu soran pencere"""
        dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=title
        )
        dialog.format_secondary_text(message)
        
        # Tamam / İptal buton etiketlerini Türkçe yapmak için
        dialog.set_default_response(Gtk.ResponseType.OK)
        
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _on_action_clicked(self, action_name, callback):
        """Tüm butonların geçeceği ortak onay kontrolü"""
        msg = _("'{0}' cihazı için '{1}' işlemini gerçekleştirmek istiyor musunuz?").format(self.name, action_name)
        if self._confirm_dialog(action_name, msg):
            callback()

    # ─── BUTON İŞLEVLERİ ───
    def _action_open_queue(self):
        print(f"{self.name} için kuyruk açılıyor...")
        # Varsa backend metodun: self.parent_window.cups.open_queue(self.name)

    def _action_print_test(self):
        if hasattr(self.parent_window.cups, 'print_test_page'):
            self.parent_window.cups.print_test_page(self.name)

    def _action_set_default(self):
        print(f"{self.name} varsayılan yapılıyor...")
        # Varsa backend metodun: self.parent_window.cups.set_default(self.name)

    def _action_pause(self):
        print(f"{self.name} duraklatılıyor...")
        # Varsa backend metodun: self.parent_window.cups.pause_printer(self.name)

    def _action_delete(self):
        if hasattr(self.parent_window.cups, 'delete_printer'):
            if self.parent_window.cups.delete_printer(self.name):
                self.parent_window.load_devices()    

    def _on_delete_printer(self):
        if self.parent_window.cups.delete_printer(self.name):
            self.parent_window.load_devices()


class MainWindow(Gtk.Window):
    def __init__(self, cups_backend=None, scanner_backend=None):
        super().__init__(title=_("Yazıcılar ve Tarayıcılar"))
        self.set_default_size(750, 600)
        load_css()

        self.cups = cups_backend if cups_backend else CupsBackend()
        self.scanner = scanner_backend if scanner_backend else ScannerBackend()
        self.notifier = NotificationManager()

        # Üst Başlık Çubuğu
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(_("Yazıcılar ve Tarayıcılar"))
        self.set_titlebar(header)

        # Üst Sağ Simgeler
        btn_lang = Gtk.Button.new_from_icon_name("preferences-desktop-locale-symbolic", Gtk.IconSize.BUTTON)
        btn_lang.get_style_context().add_class("top-icon-btn")

        btn_dark = Gtk.Button.new_from_icon_name("weather-clear-night-symbolic", Gtk.IconSize.BUTTON)
        btn_dark.get_style_context().add_class("top-icon-btn")

        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.btn_refresh.get_style_context().add_class("top-icon-btn")
        self.btn_refresh.connect("clicked", lambda x: self.load_devices())

        header.pack_end(self.btn_refresh)
        header.pack_end(btn_dark)
        header.pack_end(btn_lang)
        # Ana Kapsayıcı
        scroll = Gtk.ScrolledWindow()
        self.add(scroll)

        # spacing=10 yaparak dikeydeki elemanların arasını açıyoruz
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # PENCERENİN DÖRT BİR YANINDAN 12px NEFES PAYI BIRAKIYORUZ:
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)

        scroll.add(main_box)
        # 1. Ana Başlık
        lbl_main = Gtk.Label(label=_("Yazıcılar ve Tarayıcılar"), xalign=0)
        lbl_main.get_style_context().add_class("main-title")
        lbl_main.set_margin_left(12)
        main_box.pack_start(lbl_main, False, False, 0)

        # 2. Cihaz Ekle Kartı
        add_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        add_card.get_style_context().add_class("add-device-card")
        add_card.set_margin_left(6)
        add_card.set_margin_right(6)

        # NOTE: Yanıltıcı olan '+' simgesi (add_icon) buradan tamamen kaldırıldı.

        add_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_title = Gtk.Label(label=_("Cihaz ekle"), xalign=0)
        add_title.get_style_context().add_class("card-title")
        add_sub = Gtk.Label(label=_("Ağdaki veya USB'deki bir yazıcı ya da tarayıcı ekleyin"), xalign=0)
        add_sub.get_style_context().add_class("card-subtitle")

        add_text_box.pack_start(add_title, False, False, 0)
        add_text_box.pack_start(add_sub, False, False, 0)
        add_card.pack_start(add_text_box, True, True, 0)

        # Mavi "Cihaz ekle" Butonu
        btn_add_device = Gtk.Button(label=_("Cihaz ekle"))
        btn_add_device.get_style_context().add_class("btn-primary")
        btn_add_device.connect("clicked", self._on_add_device_clicked)
        add_card.pack_end(btn_add_device, False, False, 0)

        main_box.pack_start(add_card, False, False, 0)

        # 3. Cihazlarınız Alt Başlığı
        lbl_section = Gtk.Label(label=_("Cihazlarınız"), xalign=0)
        lbl_section.get_style_context().add_class("section-title")
        lbl_section.set_margin_left(12)
        main_box.pack_start(lbl_section, False, False, 0)

        # 4. Cihaz Listesi Konteynırı
        self.device_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.pack_start(self.device_list_box, True, True, 0)

        self.load_devices()

    def _on_add_device_clicked(self, button):
        """Cihaz Ekle butonuna tıklandığında açılan diyalog penceresi"""
        button.set_sensitive(False)
        while Gtk.events_pending():
            Gtk.main_iteration()

        dialog = AddDeviceDialog(self, self.cups, self.scanner)
        dialog.set_modal(True)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            dialog.hide()

            name, uri = dialog.get_result()
            if name and uri:
                if getattr(self.cups, 'add_printer', None):
                    if self.cups.add_printer(name, uri):
                        self.notifier.notify(_("Başarılı"), _("Cihaz başarıyla eklendi."))
                        self.load_devices()

        dialog.destroy()
        button.set_sensitive(True)

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

    def _fetch_devices(self):
        printers = self.cups.get_printers()
        scanners = self.scanner.get_scanners()
        return printers, scanners

    def _on_devices_loaded(self, result, error):
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.set_sensitive(True)

        if error:
            print("Cihazlar yüklenirken hata:", error)
            return

        printers, scanners = result

        # Yazıcıları ekle
        if isinstance(printers, dict):
            for name in printers.keys():
                card = DeviceCard(name, "printer", _("Boşta"), self)
                self.device_list_box.pack_start(card, False, False, 0)

        # Tarayıcıları ekle
        if isinstance(scanners, dict):
            for dev_id, info in scanners.items():
                name = info.get('description', dev_id) if isinstance(info, dict) else str(dev_id)
                card = DeviceCard(name, "scanner", _("Hazır (Tarayıcı)"), self)
                self.device_list_box.pack_start(card, False, False, 0)
        elif isinstance(scanners, list):
            for sc in scanners:
                name = sc.get('description', sc.get('name', 'Bilinmeyen Tarayıcı')) if isinstance(sc, dict) else str(sc)
                card = DeviceCard(name, "scanner", _("Hazır (Tarayıcı)"), self)
                self.device_list_box.pack_start(card, False, False, 0)

        self.device_list_box.show_all()