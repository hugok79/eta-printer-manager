import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
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

        # 1. Auto-Refresh Setup (Every 2 seconds)
        self.timeout_id = GLib.timeout_add_seconds(2, self._auto_refresh_callback)
        self.connect("destroy", self.on_window_destroy)

        # Initial Load
        self.refresh_queue()

    def _auto_refresh_callback(self):
        """GTK GLib timer callback."""
        self.refresh_queue()
        return True  # Keep timer alive

    def on_window_destroy(self, widget):
        """Stops the timer on window close to prevent memory leaks."""
        if hasattr(self, 'timeout_id') and self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

    def refresh_queue(self):
        """Smart update: modifies treeview without clearing to prevent flicker and selection loss."""
        jobs = self.backend.get_print_jobs(self.printer_name)
        new_jobs_map = {str(j["job_id"]): j for j in jobs}

        # 1. Scan current items in store
        existing_iters = {}
        treeiter = self.store.get_iter_first()
        while treeiter:
            job_id = self.store.get_value(treeiter, 0)
            existing_iters[job_id] = treeiter
            treeiter = self.store.iter_next(treeiter)

        # 2. Remove completed/cancelled jobs from store
        for job_id, treeiter in list(existing_iters.items()):
            if job_id not in new_jobs_map:
                self.store.remove(treeiter)

        # 3. Add new jobs or update existing ones
        for job_id, job in new_jobs_map.items():
            user = str(job.get("user", _("Unknown")))
            size = str(job.get("size", ""))
            time_str = str(job.get("time", ""))

            if job_id in existing_iters:
                # Update cells if they changed
                treeiter = existing_iters[job_id]
                if self.store.get_value(treeiter, 1) != user:
                    self.store.set_value(treeiter, 1, user)
                if self.store.get_value(treeiter, 2) != size:
                    self.store.set_value(treeiter, 2, size)
                if self.store.get_value(treeiter, 3) != time_str:
                    self.store.set_value(treeiter, 3, time_str)
            else:
                # Append new job
                self.store.append([job_id, user, size, time_str])

    def on_refresh_clicked(self, widget):
        self.refresh_queue()

    def on_cancel_job_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            job_id = model[treeiter][0]
            if self.backend.cancel_job(job_id):
                self.refresh_queue()