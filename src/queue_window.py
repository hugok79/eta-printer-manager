import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from src.cups_backend import CupsBackend
from src.locale_config import _

class PrintQueueWindow(Gtk.Window):
    """Standalone GTK3 window for managing printer queues."""

    def __init__(self, printer_name: str, parent_window=None):
        super().__init__(title=_("Print Queue - {0}").format(printer_name))
        self.printer_name = printer_name

        # Initialize backend instance
        self.backend = CupsBackend()

        if parent_window:
            top_win = parent_window
            if hasattr(parent_window, 'window'):
                top_win = parent_window.window
            elif hasattr(parent_window, 'get_toplevel'):
                top_win = parent_window.get_toplevel()

            if isinstance(top_win, Gtk.Window):
                self.set_transient_for(top_win)
            
        self.set_default_size(550, 350)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        # Layout Box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_left(12)
        vbox.set_margin_right(12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        self.add(vbox)

        # ListStore: [Job ID, User, Size, Time]
        self.store = Gtk.ListStore(str, str, str, str)
        self.treeview = Gtk.TreeView(model=self.store)

        columns = [
            (_("Job ID"), 0),
            (_("User"), 1),
            (_("Size"), 2),
            (_("Submitted Time"), 3)
        ]

        for title, col_id in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=col_id)
            column.set_resizable(True)
            self.treeview.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(self.treeview)
        vbox.pack_start(scroll, True, True, 0)

        # Bottom Button Bar
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.btn_refresh = Gtk.Button(label=_("Refresh"))
        self.btn_refresh.connect("clicked", self.on_refresh_clicked)
        btn_box.pack_start(self.btn_refresh, False, False, 0)

        self.btn_cancel_job = Gtk.Button(label=_("Cancel Job"))
        self.btn_cancel_job.get_style_context().add_class("destructive-action")
        self.btn_cancel_job.connect("clicked", self.on_cancel_job_clicked)
        btn_box.pack_end(self.btn_cancel_job, False, False, 0)

        vbox.pack_start(btn_box, False, False, 0)

        # Initial Load
        self.refresh_queue()

    def refresh_queue(self):
        """Reloads active jobs into the treeview."""
        self.store.clear()
        jobs = self.backend.get_print_jobs(self.printer_name)
        for job in jobs:
            self.store.append([
                str(job.get("job_id", "")),
                str(job.get("user", "")),
                str(job.get("size", "")),
                str(job.get("time", ""))
            ])

    def on_refresh_clicked(self, widget):
        self.refresh_queue()

    def on_cancel_job_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            job_id = model[treeiter][0]
            if self.backend.cancel_job(job_id):
                self.refresh_queue()