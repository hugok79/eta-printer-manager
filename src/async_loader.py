import threading
from gi.repository import GLib

class AsyncLoader:
    @staticmethod
    def run_async(task_func, callback):
        def thread_target():
            try:
                result = task_func()
                GLib.idle_add(callback, result, None)
            except Exception as e:
                GLib.idle_add(callback, None, e)

        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()