"""
Windows POC: Exclude an overlay window from screen capture.

Uses Win32 API SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE (0x11).
Expected behavior on Windows 10 2004+ and Windows 11:
- The overlay is visible on the physical display.
- The overlay is hidden in most capture APIs (screen recording, screen share, screenshots).
"""

import ctypes
from ctypes import wintypes
import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox
import traceback


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
GA_ROOT = 2

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011


SetWindowDisplayAffinity = user32.SetWindowDisplayAffinity
SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
SetWindowDisplayAffinity.restype = wintypes.BOOL

GetWindowDisplayAffinity = user32.GetWindowDisplayAffinity
GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetWindowDisplayAffinity.restype = wintypes.BOOL

GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = ctypes.c_long

SetWindowLongW = user32.SetWindowLongW
SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
SetWindowLongW.restype = ctypes.c_long

GetAncestor = user32.GetAncestor
GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
GetAncestor.restype = wintypes.HWND


def _resolve_log_path() -> str:
    env_log = os.environ.get("POC_LOGFILE", "").strip()
    if env_log:
        return env_log
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "poc_launcher.log")


LOG_PATH = _resolve_log_path()


def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def log_line(message: str) -> None:
    logging.info(message)


def install_global_exception_logger() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("Unhandled exception:\n%s", text)
        # Keep default behavior for visibility when launched from terminal.
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def set_display_affinity(hwnd: int, mode: int) -> tuple[bool, int]:
    kernel32.SetLastError(0)
    ok = bool(SetWindowDisplayAffinity(hwnd, mode))
    err = kernel32.GetLastError()
    return ok, err


def get_display_affinity(hwnd: int) -> tuple[bool, int, int]:
    value = wintypes.DWORD(0)
    kernel32.SetLastError(0)
    ok = bool(GetWindowDisplayAffinity(hwnd, ctypes.byref(value)))
    err = kernel32.GetLastError()
    return ok, int(value.value), err


def style_as_overlay(hwnd: int) -> None:
    ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex_style |= WS_EX_TOOLWINDOW
    ex_style |= WS_EX_NOACTIVATE
    SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)


def get_top_level_hwnd(hwnd: int) -> int:
    root = int(GetAncestor(wintypes.HWND(hwnd), GA_ROOT))
    return root if root else hwnd


class CaptureExclusionPOC:
    def __init__(self) -> None:
        log_line("Initializing tkinter window")
        self.root = tk.Tk()
        self.root.report_callback_exception = self._tk_callback_exception
        self.root.title("Cheatly Windows Capture Exclusion POC")
        self.root.geometry("560x220+120+120")
        self.root.configure(bg="#c1121f")
        self.root.attributes("-topmost", True)

        title = tk.Label(
            self.root,
            text="Cheatly Windows Capture Exclusion POC",
            bg="#c1121f",
            fg="white",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(pady=(16, 8))

        msg = (
            "This window should remain visible locally but be hidden in capture.\n"
            "Use Enable/Disable buttons to compare behavior in OBS/Zoom/Meet."
        )
        subtitle = tk.Label(
            self.root,
            text=msg,
            bg="#c1121f",
            fg="white",
            font=("Segoe UI", 10),
            justify="center",
        )
        subtitle.pack()

        self.status = tk.Label(
            self.root,
            text="Status: initializing...",
            bg="#c1121f",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.status.pack(pady=(14, 10))

        row = tk.Frame(self.root, bg="#c1121f")
        row.pack()

        tk.Button(row, text="Enable Exclusion", command=self.enable).grid(row=0, column=0, padx=6)
        tk.Button(row, text="Disable Exclusion", command=self.disable).grid(row=0, column=1, padx=6)
        tk.Button(row, text="Read Affinity", command=self.read_affinity).grid(row=0, column=2, padx=6)
        tk.Button(row, text="Exit", command=self.root.destroy).grid(row=0, column=3, padx=6)

        self.root.update_idletasks()
        self.hwnd = get_top_level_hwnd(self.root.winfo_id())
        log_line(f"Resolved top-level HWND: {self.hwnd}")
        style_as_overlay(self.hwnd)
        log_line("Applied overlay extended styles")
        self.root.after(200, self.enable)

    def _tk_callback_exception(self, exc, val, tb) -> None:
        text = "".join(traceback.format_exception(exc, val, tb))
        logging.error("Tk callback exception:\n%s", text)
        try:
            messagebox.showerror("Unhandled GUI error", str(val))
        except Exception:
            pass

    def _set_status(self, text: str) -> None:
        self.status.config(text=text)
        log_line(text)

    def enable(self) -> None:
        log_line("Enable requested: trying WDA_EXCLUDEFROMCAPTURE (0x11)")
        ok, err = set_display_affinity(self.hwnd, WDA_EXCLUDEFROMCAPTURE)
        if ok:
            self._set_status("Status: WDA_EXCLUDEFROMCAPTURE enabled (0x11)")
        else:
            # ERROR_INVALID_PARAMETER (87) is common when 0x11 is unsupported,
            # or if a non-top-level/invalid hwnd is passed.
            if err == 87:
                log_line("0x11 failed with Win32 error 87, trying fallback WDA_MONITOR (0x01)")
                fallback_ok, fallback_err = set_display_affinity(self.hwnd, WDA_MONITOR)
                if fallback_ok:
                    self._set_status(
                        "Status: 0x11 unsupported here; fallback WDA_MONITOR enabled (0x01)"
                    )
                    messagebox.showwarning(
                        "WDA_EXCLUDEFROMCAPTURE unsupported",
                        "SetWindowDisplayAffinity returned Win32 error 87 for 0x11.\n\n"
                        "Fallback WDA_MONITOR (0x01) has been enabled.\n"
                        "This may show black/blank in some capture paths instead of full exclusion.\n\n"
                        "Likely causes:\n"
                        "- Windows build does not support 0x11\n"
                        "- Capture path does not honor 0x11\n"
                        "- Window manager/composition constraints",
                    )
                    return
                self._set_status(
                    f"Status: enable failed (0x11 err=87; fallback 0x01 err={fallback_err})"
                )
            else:
                self._set_status(f"Status: enable failed, Win32 error={err}")
            messagebox.showerror(
                "SetWindowDisplayAffinity failed",
                f"Could not enable capture exclusion.\nWin32 error: {err}",
            )

    def disable(self) -> None:
        log_line("Disable requested: setting WDA_NONE (0x00)")
        ok, err = set_display_affinity(self.hwnd, WDA_NONE)
        if ok:
            self._set_status("Status: affinity reset to WDA_NONE (0x00)")
        else:
            self._set_status(f"Status: disable failed, Win32 error={err}")
            messagebox.showerror(
                "SetWindowDisplayAffinity failed",
                f"Could not disable capture exclusion.\nWin32 error: {err}",
            )

    def read_affinity(self) -> None:
        log_line("Read affinity requested")
        ok, value, err = get_display_affinity(self.hwnd)
        if ok:
            self._set_status(f"Status: current affinity=0x{value:02X}")
        else:
            self._set_status(f"Status: read failed, Win32 error={err}")

    def run(self) -> None:
        log_line("Entering tkinter main loop")
        self.root.mainloop()
        log_line("Exited tkinter main loop")


def main() -> None:
    setup_logging()
    install_global_exception_logger()
    log_line("=== Windows capture exclusion POC start ===")
    log_line(f"Log file: {LOG_PATH}")

    if sys.platform != "win32":
        log_line("This POC must be run on Windows.")
        return

    win_ver = sys.getwindowsversion()
    log_line(
        "Windows version: "
        f"major={win_ver.major} minor={win_ver.minor} build={win_ver.build}"
    )
    log_line("Note: WDA_EXCLUDEFROMCAPTURE generally requires Windows 10 build 19041+.")

    app = CaptureExclusionPOC()
    app.run()
    log_line("=== Windows capture exclusion POC end ===")


if __name__ == "__main__":
    main()
