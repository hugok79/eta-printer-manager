import os

def get_version():
    """Reads application version from local dev tree or system installation path."""
    version = "0.0.0"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Check local build/dev path (__version__ in project root)
    local_path = os.path.join(base_dir, "..", "__version__")
    
    # 2. Check system installation path
    system_path = "/usr/share/pardus/eta-printer-manager/__version__"
    
    version_file = local_path if os.path.exists(local_path) else system_path

    try:
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                version = f.readline().strip()
    except Exception as e:
        print(f"Failed to read version file: {e}")

    return version

# Kolay erişim için değişken olarak dışa aktar
__version__ = get_version()