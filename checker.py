import subprocess
import threading
from db import update_tool_status, get_tool_statuses

CONTAINER_NAME = "dockshade"

BINARY_MAP = {
    "metasploit":   "msfconsole",
    "theHarvester": "theHarvester",
    "aircrack-ng":  "aircrack-ng",
    "enum4linux":   "enum4linux",
    "burpsuite":    "burpsuite",
    "john":         "john",
    "hashcat":      "hashcat",
    "netexec":      "netexec",
    "linpeas":      "linpeas.sh",
    "winpeas":      "winPEASx64.exe",
    "volatility":   "volatility3",
}

def _binary_for(tool_name):
    return BINARY_MAP.get(tool_name, tool_name)

def _distrobox_ok():
    try:
        r = subprocess.run(
            ["distrobox", "--version"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False

def _check_single(name):
    binary = _binary_for(name)
    try:
        r = subprocess.run(
            ["distrobox", "enter", CONTAINER_NAME, "--", "which", binary],
            capture_output=True, timeout=8
        )
        return r.returncode == 0
    except Exception:
        return False

def check_all_tools(tool_names, on_result=None, on_done=None):
    if not _distrobox_ok():
        if on_done:
            on_done()
        return

    def _worker():
        for name in tool_names:
            installed = _check_single(name)
            update_tool_status(name, installed)
            if on_result:
                on_result(name, installed)
        if on_done:
            on_done()

    threading.Thread(target=_worker, daemon=True).start()

def get_cached_statuses(tool_names, json_defaults):
    cached = get_tool_statuses()
    return {n: cached.get(n, json_defaults.get(n, True)) for n in tool_names}
