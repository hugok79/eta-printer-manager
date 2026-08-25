import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from src.cups_backend import CupsBackend
from src.locale_config import _


class PrintQueueWindow(Gtk.Window):

    def __init__(self, printer_name, parent_window=None):
        super().__init__(title=_("Print Queue - {0}").format(printer_name))
        self.printer_name = printer_name
        self.backend = CupsBackend()
        self._timeout_id = None

        if parent_window:
            top = parent_window
            if hasattr(parent_window, "window"):
                top = parent_window.window
            elif hasattr(parent_window, "get_toplevel"):
                top = parent_window.get_toplevel()
            if isinstance(top, Gtk.Window):
                self.set_transient_for(top)

        self.set_default_size(550, 350)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        self.add(vbox)

        self.store = Gtk.ListStore(str, str, str, str)
        treeview = Gtk.TreeView(model=self.store)

        for title, col_id in [(_("Job ID"), 0), (_("User"), 1), (_("Size"), 2), (_("Submitted Time"), 3)]:
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=col_id)
            col.set_resizable(True)
            treeview.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.add(treeview)
        vbox.pack_start(scroll, True, True, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_cancel = Gtk.Button(label=_("Cancel Job"))
        btn_cancel.get_style_context().add_class("destructive-action")
        btn_cancel.connect("clicked", self._on_cancel_job, treeview)
        btn_box.pack_end(btn_cancel, False, False, 0)
        vbox.pack_start(btn_box, False, False, 0)

        self._timeout_id = GLib.timeout_add_seconds(1, self._tick)
        self.connect("destroy", self._on_destroy)
        self._tick()

    def _tick(self):
        self._refresh()
        return True

    def _on_destroy(self, _widget):
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def _refresh(self):
        jobs = self.backend.get_print_jobs(self.printer_name)
        new = {str(j["job_id"]): j for j in jobs}

        existing = {}
        it = self.store.get_iter_first()
        while it:
            existing[self.store.get_value(it, 0)] = it
            it = self.store.iter_next(it)

        for jid, it in list(existing.items()):
            if jid not in new:
                self.store.remove(it)

        for jid, job in new.items():
            user = str(job.get("user", _("Unknown")))
            size = str(job.get("size", ""))
            time_s = str(job.get("time", ""))

            if jid in existing:
                it = existing[jid]
                if self.store.get_value(it, 1) != user:
                    self.store.set_value(it, 1, user)
                if self.store.get_value(it, 2) != size:
                    self.store.set_value(it, 2, size)
                if self.store.get_value(it, 3) != time_s:
                    self.store.set_value(it, 3, time_s)
            else:
                self.store.append([jid, user, size, time_s])

    def _on_cancel_job(self, _button, treeview):
        _, it = treeview.get_selection().get_selected()
        if it:
            jid = self.store[it][0]
            if self.backend.cancel_job(jid):
                self._refresh()
