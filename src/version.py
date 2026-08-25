import os


def get_version():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "__version__"),
        "/usr/share/pardus/eta-printer-manager/__version__",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return f.readline().strip()
            except Exception:
                pass
    return "0.0.0"


__version__ = get_version()
