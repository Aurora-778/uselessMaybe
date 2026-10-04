"""A three-second Windows toast born without any ability to activate the window.

The launcher only reports whether the detached child was accepted. The child
creates a native layered popup with NOACTIVATE on CreateWindowExW itself, paints
into a premultiplied ARGB DIB with GDI+, and exits after its display deadline.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
from pathlib import Path
import subprocess
import sys
import time


WIDTH = 420
HEIGHT = 138
MARGIN = 18
MAX_MESSAGE = 180

WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
MONITOR_DEFAULTTONEAREST = 2
ERROR_ALREADY_EXISTS = 183
ULW_ALPHA = 0x00000002
AC_SRC_ALPHA = 1
PM_REMOVE = 1
WM_MOUSEACTIVATE = 0x0021
WM_NCHITTEST = 0x0084
MA_NOACTIVATEANDEAT = 4
HTTRANSPARENT = -1
FR_PRIVATE = 0x10
PIXEL_FORMAT_32BPP_PARGB = 0x000E200B
UNIT_PIXEL = 2


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", wintypes.BYTE), ("BlendFlags", wintypes.BYTE),
                ("SourceConstantAlpha", wintypes.BYTE), ("AlphaFormat", wintypes.BYTE)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 1)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                ("lpfnWndProc", ctypes.c_void_p), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p), ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", ctypes.c_void_p)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", wintypes.UINT),
                ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t),
                ("time", wintypes.DWORD), ("pt", POINT), ("lPrivate", wintypes.DWORD)]


class GDIPLUS_STARTUP_INPUT(ctypes.Structure):
    _fields_ = [("GdiplusVersion", wintypes.UINT), ("DebugEventCallback", ctypes.c_void_p),
                ("SuppressBackgroundThread", wintypes.BOOL),
                ("SuppressExternalCodecs", wintypes.BOOL)]


class GPRECTF(ctypes.Structure):
    _fields_ = [("X", ctypes.c_float), ("Y", ctypes.c_float),
                ("Width", ctypes.c_float), ("Height", ctypes.c_float)]


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "show_toast.py"


def _python_without_console() -> Path:
    executable = Path(sys.executable)
    sibling = executable.with_name("pythonw.exe")
    return sibling if sibling.is_file() else executable


def _bounded_message(message: str) -> str:
    clean = message.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return clean[: MAX_MESSAGE - 1] + "…" if len(clean) > MAX_MESSAGE else clean


def launch_toast(message: str) -> bool:
    """Launch without waiting. True means accepted, never proof of display."""
    if sys.platform != "win32" or not isinstance(message, str) or not message.strip():
        return False
    script = _script_path()
    if not script.is_file():
        return False
    executable = _python_without_console()
    flags = (subprocess.DETACHED_PROCESS if executable.name.lower() == "pythonw.exe"
             else subprocess.CREATE_NO_WINDOW)
    try:
        subprocess.Popen(
            [str(executable), "-I", str(script), "--message", _bounded_message(message)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, creationflags=flags,
        )
    except (OSError, ValueError):
        return False
    return True


def _place(work: RECT, width: int = WIDTH, height: int = HEIGHT,
           margin: int = MARGIN) -> tuple[int, int]:
    """Position within a signed monitor work area, clear of the taskbar."""
    return max(work.left, work.right - width - margin), max(work.top, work.bottom - height - margin)


def _wrap_pixels(text: str, measure, max_width: float) -> list[str]:
    """Preserve explicit lines and split long unspaced words by measured width."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph or measure(paragraph) <= max_width:
            lines.append(paragraph)
            continue
        current = ""
        for word in paragraph.split(" "):
            while measure(word) > max_width:
                if current:
                    lines.append(current)
                    current = ""
                cut = 1
                while cut < len(word) and measure(word[:cut + 1]) <= max_width:
                    cut += 1
                lines.append(word[:cut])
                word = word[cut:]
            if not word and not current:
                continue
            candidate = word if not current else current + " " + word
            if measure(candidate) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _fit_lines(text: str, measure, line_height: float,
               max_width: float, max_height: float) -> list[str]:
    lines = _wrap_pixels(text, measure, max_width)
    allowed = max(1, int(max_height // line_height))
    if len(lines) <= allowed:
        return lines
    lines = lines[:allowed]
    last = lines[-1]
    while last and measure(last + "…") > max_width:
        last = last[:-1]
    lines[-1] = last + "…"
    return lines


def _bind(dll, name: str, restype, *argtypes):
    function = getattr(dll, name)
    function.argtypes = list(argtypes)
    function.restype = restype
    return function


def _check(status: int, operation: str) -> None:
    if status:
        raise OSError(f"GDI+ {operation} failed ({status})")


class _Native:
    """Typed Windows functions, loaded only in the toast child."""

    def __init__(self):
        p = ctypes.c_void_p
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.gdi = ctypes.WinDLL("gdi32", use_last_error=True)
        self.gp = ctypes.WinDLL("gdiplus", use_last_error=True)

        _bind(self.user, "GetForegroundWindow", p)
        _bind(self.user, "MonitorFromWindow", p, p, wintypes.DWORD)
        _bind(self.user, "GetMonitorInfoW", wintypes.BOOL, p, ctypes.POINTER(MONITORINFO))
        _bind(self.user, "DefWindowProcW", ctypes.c_ssize_t, p, wintypes.UINT,
              ctypes.c_size_t, ctypes.c_ssize_t)
        _bind(self.user, "RegisterClassExW", wintypes.ATOM, ctypes.POINTER(WNDCLASSEXW))
        _bind(self.user, "UnregisterClassW", wintypes.BOOL, wintypes.LPCWSTR, p)
        _bind(self.user, "CreateWindowExW", p, wintypes.DWORD, wintypes.LPCWSTR,
              wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int,
              ctypes.c_int, ctypes.c_int, p, p, p, p)
        _bind(self.user, "DestroyWindow", wintypes.BOOL, p)
        _bind(self.user, "SetWindowPos", wintypes.BOOL, p, p, ctypes.c_int,
              ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
        _bind(self.user, "IsWindowVisible", wintypes.BOOL, p)
        _bind(self.user, "UpdateLayeredWindow", wintypes.BOOL, p, p,
              ctypes.POINTER(POINT), ctypes.POINTER(SIZE), p,
              ctypes.POINTER(POINT), wintypes.DWORD,
              ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD)
        _bind(self.user, "PeekMessageW", wintypes.BOOL, ctypes.POINTER(MSG), p,
              wintypes.UINT, wintypes.UINT, wintypes.UINT)
        _bind(self.user, "TranslateMessage", wintypes.BOOL, ctypes.POINTER(MSG))
        _bind(self.user, "DispatchMessageW", ctypes.c_ssize_t, ctypes.POINTER(MSG))
        try:
            _bind(self.user, "SetProcessDpiAwarenessContext", wintypes.BOOL, p)
        except AttributeError:
            pass

        _bind(self.kernel, "GetModuleHandleW", p, wintypes.LPCWSTR)
        _bind(self.kernel, "CreateMutexW", p, p, wintypes.BOOL, wintypes.LPCWSTR)
        _bind(self.kernel, "CloseHandle", wintypes.BOOL, p)
        _bind(self.gdi, "CreateCompatibleDC", p, p)
        _bind(self.gdi, "CreateDIBSection", p, p, ctypes.POINTER(BITMAPINFO),
              wintypes.UINT, ctypes.POINTER(p), p, wintypes.DWORD)
        _bind(self.gdi, "SelectObject", p, p, p)
        _bind(self.gdi, "DeleteObject", wintypes.BOOL, p)
        _bind(self.gdi, "DeleteDC", wintypes.BOOL, p)

        _bind(self.gp, "GdiplusStartup", ctypes.c_int, ctypes.POINTER(ctypes.c_size_t),
              ctypes.POINTER(GDIPLUS_STARTUP_INPUT), p)
        _bind(self.gp, "GdiplusShutdown", None, ctypes.c_size_t)
        _bind(self.gp, "GdipCreateBitmapFromScan0", ctypes.c_int, ctypes.c_int,
              ctypes.c_int, ctypes.c_int, ctypes.c_int, p, ctypes.POINTER(p))
        _bind(self.gp, "GdipGetImageGraphicsContext", ctypes.c_int, p, ctypes.POINTER(p))
        _bind(self.gp, "GdipGraphicsClear", ctypes.c_int, p, wintypes.DWORD)
        _bind(self.gp, "GdipSetSmoothingMode", ctypes.c_int, p, ctypes.c_int)
        _bind(self.gp, "GdipSetInterpolationMode", ctypes.c_int, p, ctypes.c_int)
        _bind(self.gp, "GdipCreatePath", ctypes.c_int, ctypes.c_int, ctypes.POINTER(p))
        _bind(self.gp, "GdipAddPathArc", ctypes.c_int, p, ctypes.c_float,
              ctypes.c_float, ctypes.c_float, ctypes.c_float,
              ctypes.c_float, ctypes.c_float)
        _bind(self.gp, "GdipClosePathFigure", ctypes.c_int, p)
        _bind(self.gp, "GdipDeletePath", ctypes.c_int, p)
        _bind(self.gp, "GdipCreateSolidFill", ctypes.c_int, wintypes.DWORD, ctypes.POINTER(p))
        _bind(self.gp, "GdipDeleteBrush", ctypes.c_int, p)
        _bind(self.gp, "GdipFillPath", ctypes.c_int, p, p, p)
        _bind(self.gp, "GdipFillPolygonI", ctypes.c_int, p, p,
              ctypes.POINTER(POINT), ctypes.c_int, ctypes.c_int)
        _bind(self.gp, "GdipLoadImageFromFile", ctypes.c_int, wintypes.LPCWSTR, ctypes.POINTER(p))
        _bind(self.gp, "GdipGetImageWidth", ctypes.c_int, p, ctypes.POINTER(wintypes.UINT))
        _bind(self.gp, "GdipGetImageHeight", ctypes.c_int, p, ctypes.POINTER(wintypes.UINT))
        _bind(self.gp, "GdipDrawImageRectRectI", ctypes.c_int, p, p,
              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
              ctypes.c_int, p, p, p)
        _bind(self.gp, "GdipDisposeImage", ctypes.c_int, p)
        _bind(self.gp, "GdipDeleteGraphics", ctypes.c_int, p)
        _bind(self.gp, "GdipFlush", ctypes.c_int, p, ctypes.c_int)
        _bind(self.gp, "GdipNewPrivateFontCollection", ctypes.c_int, ctypes.POINTER(p))
        _bind(self.gp, "GdipPrivateAddFontFile", ctypes.c_int, p, wintypes.LPCWSTR)
        _bind(self.gp, "GdipDeletePrivateFontCollection", ctypes.c_int, ctypes.POINTER(p))
        _bind(self.gp, "GdipCreateFontFamilyFromName", ctypes.c_int,
              wintypes.LPCWSTR, p, ctypes.POINTER(p))
        _bind(self.gp, "GdipDeleteFontFamily", ctypes.c_int, p)
        _bind(self.gp, "GdipCreateFont", ctypes.c_int, p, ctypes.c_float,
              ctypes.c_int, ctypes.c_int, ctypes.POINTER(p))
        _bind(self.gp, "GdipDeleteFont", ctypes.c_int, p)
        _bind(self.gp, "GdipGetFontHeight", ctypes.c_int, p, p, ctypes.POINTER(ctypes.c_float))
        _bind(self.gp, "GdipCreateStringFormat", ctypes.c_int, ctypes.c_int,
              wintypes.WORD, ctypes.POINTER(p))
        _bind(self.gp, "GdipDeleteStringFormat", ctypes.c_int, p)
        _bind(self.gp, "GdipMeasureString", ctypes.c_int, p, wintypes.LPCWSTR,
              ctypes.c_int, p, ctypes.POINTER(GPRECTF), p,
              ctypes.POINTER(GPRECTF), p, p)
        _bind(self.gp, "GdipDrawString", ctypes.c_int, p, wintypes.LPCWSTR,
              ctypes.c_int, p, ctypes.POINTER(GPRECTF), p, p)


def _monitor_and_dpi(native: _Native, foreground: int) -> tuple[RECT, float]:
    monitor = native.user.MonitorFromWindow(foreground, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not monitor or not native.user.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    scale = 1.0
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        get_dpi = _bind(shcore, "GetDpiForMonitor", ctypes.c_long, ctypes.c_void_p,
                        ctypes.c_int, ctypes.POINTER(wintypes.UINT), ctypes.POINTER(wintypes.UINT))
        x_dpi = wintypes.UINT()
        y_dpi = wintypes.UINT()
        if get_dpi(monitor, 0, ctypes.byref(x_dpi), ctypes.byref(y_dpi)) == 0 and x_dpi.value:
            scale = x_dpi.value / 96.0
    except (AttributeError, OSError):
        pass
    return info.rcWork, scale


def _rounded_path(native: _Native, width: int, height: int, radius: float):
    path = ctypes.c_void_p()
    _check(native.gp.GdipCreatePath(0, ctypes.byref(path)), "create path")
    d = radius * 2
    for x, y, angle in ((0, 0, 180), (width - d, 0, 270),
                        (width - d, height - d, 0), (0, height - d, 90)):
        _check(native.gp.GdipAddPathArc(path, x, y, d, d, angle, 90), "add rounded corner")
    _check(native.gp.GdipClosePathFigure(path), "close path")
    return path


def _solid(native: _Native, argb: int):
    brush = ctypes.c_void_p()
    _check(native.gp.GdipCreateSolidFill(argb, ctypes.byref(brush)), "create brush")
    return brush


def _font_family(native: _Native, preferred: str, collection):
    family = ctypes.c_void_p()
    if collection and native.gp.GdipCreateFontFamilyFromName(preferred, collection, ctypes.byref(family)) == 0:
        return family
    _check(native.gp.GdipCreateFontFamilyFromName("Segoe UI", None, ctypes.byref(family)),
           "fallback font family")
    return family


def _font(native: _Native, family, size: float, bold: bool = False):
    font = ctypes.c_void_p()
    _check(native.gp.GdipCreateFont(family, size, 1 if bold else 0,
                                    UNIT_PIXEL, ctypes.byref(font)), "create font")
    return font


def _measure(native: _Native, graphics, font, fmt, text: str) -> float:
    if not text:
        return 0.0
    bounds = GPRECTF()
    layout = GPRECTF(0, 0, 10000, 1000)
    _check(native.gp.GdipMeasureString(graphics, text, len(text), font,
                                       ctypes.byref(layout), fmt, ctypes.byref(bounds),
                                       None, None), "measure text")
    return bounds.Width


def _draw_text(native: _Native, graphics, text: str, font, brush, fmt,
               x: float, y: float, width: float, height: float) -> None:
    layout = GPRECTF(x, y, width, height)
    _check(native.gp.GdipDrawString(graphics, text, len(text), font,
                                    ctypes.byref(layout), fmt, brush), "draw text")


def _render(native: _Native, graphics, width: int, height: int,
            scale: float, message: str, assets: Path) -> None:
    gp = native.gp
    created: list[tuple[str, object]] = []

    def keep(kind: str, value):
        created.append((kind, value))
        return value

    try:
        _check(gp.GdipGraphicsClear(graphics, 0x00000000), "clear bitmap")
        _check(gp.GdipSetSmoothingMode(graphics, 4), "antialias")
        _check(gp.GdipSetInterpolationMode(graphics, 7), "image interpolation")
        path = keep("path", _rounded_path(native, width, height, 22 * scale))
        cream = keep("brush", _solid(native, 0xFFFFF9EB))
        _check(gp.GdipFillPath(graphics, cream, path), "draw card")

        avatar_path = assets / "curry-toast.png"
        if avatar_path.is_file():
            image = ctypes.c_void_p()
            _check(gp.GdipLoadImageFromFile(str(avatar_path), ctypes.byref(image)), "load CurryDog")
            keep("image", image)
            image_width, image_height = wintypes.UINT(), wintypes.UINT()
            _check(gp.GdipGetImageWidth(image, ctypes.byref(image_width)), "avatar width")
            _check(gp.GdipGetImageHeight(image, ctypes.byref(image_height)), "avatar height")
            ratio = min(128 / image_width.value, 120 / image_height.value)
            avatar_width, avatar_height = image_width.value * ratio, image_height.value * ratio
            _check(gp.GdipDrawImageRectRectI(graphics, image,
                  round((10 + (128 - avatar_width) / 2) * scale),
                  round((8 + (120 - avatar_height) / 2) * scale),
                  round(avatar_width * scale), round(avatar_height * scale),
                  0, 0, image_width.value, image_height.value, UNIT_PIXEL, None, None, None), "draw CurryDog")

        collection = ctypes.c_void_p()
        if gp.GdipNewPrivateFontCollection(ctypes.byref(collection)) == 0:
            keep("collection", collection)
            for filename in ("PatrickHand-Regular.ttf", "KNMaiyuan-Regular.ttf"):
                font_path = assets / filename
                if font_path.is_file():
                    gp.GdipPrivateAddFontFile(collection, str(font_path))
        brand_family = keep("family", _font_family(native, "KN Maiyuan", collection))
        body_family = keep("family", _font_family(native, "Patrick Hand", collection))
        brand_font = keep("font", _font(native, brand_family, 12 * scale, True))
        sage = keep("brush", _solid(native, 0xFF779E79))
        dark = keep("brush", _solid(native, 0xFF3D4140))
        gold = keep("brush", _solid(native, 0xFFF3C95C))
        fmt = ctypes.c_void_p()
        _check(gp.GdipCreateStringFormat(0, 0, ctypes.byref(fmt)), "create text format")
        keep("format", fmt)
        _draw_text(native, graphics, "uselessMaybe", brand_font, sage, fmt,
                   146 * scale, 17 * scale, 210 * scale, 25 * scale)

        star_coordinates = ((371, 19), (374, 27), (382, 30), (374, 33),
                            (371, 41), (368, 33), (360, 30), (368, 27))
        star = (POINT * len(star_coordinates))(
            *(POINT(round(x * scale), round(y * scale)) for x, y in star_coordinates))
        _check(gp.GdipFillPolygonI(graphics, gold, star, len(star_coordinates), 0), "draw star")

        max_width = 267 * scale
        max_height = 90 * scale
        chosen = None
        for logical_size in (18, 17, 16, 15, 14, 13, 12, 11, 10):
            font = _font(native, body_family, logical_size * scale)
            line_height = ctypes.c_float()
            _check(gp.GdipGetFontHeight(font, graphics, ctypes.byref(line_height)), "font height")
            measure = lambda value: _measure(native, graphics, font, fmt, value)
            lines = _wrap_pixels(message, measure, max_width)
            if line_height.value * len(lines) <= max_height:
                chosen = (font, line_height.value, lines)
                break
            if logical_size == 10:
                chosen = (font, line_height.value,
                          _fit_lines(message, measure, line_height.value, max_width, max_height))
            else:
                gp.GdipDeleteFont(font)
        assert chosen is not None
        font, line_height, lines = chosen
        keep("font", font)
        y = (40 * scale) + max(0.0, (max_height - line_height * len(lines)) / 2)
        for line in lines:
            if line:
                _draw_text(native, graphics, line, font, dark, fmt,
                           146 * scale, y, max_width, line_height + 4 * scale)
            y += line_height
        _check(gp.GdipFlush(graphics, 1), "flush card")
    finally:
        # GDI+ objects remain valid through the synchronous flush above.
        for kind, value in reversed(created):
            if kind == "path": gp.GdipDeletePath(value)
            elif kind == "brush": gp.GdipDeleteBrush(value)
            elif kind == "image": gp.GdipDisposeImage(value)
            elif kind == "font": gp.GdipDeleteFont(value)
            elif kind == "family": gp.GdipDeleteFontFamily(value)
            elif kind == "format": gp.GdipDeleteStringFormat(value)
            elif kind == "collection": gp.GdipDeletePrivateFontCollection(ctypes.byref(value))


def show_toast(message: str, duration: float = 3.0) -> bool:
    """Show the native popup in this child, then exit; preview can set duration."""
    if (sys.platform != "win32" or not isinstance(message, str) or not message.strip()
            or not math.isfinite(duration) or duration <= 0):
        return False
    native = _Native()
    user, kernel, gdi, gp = native.user, native.kernel, native.gdi, native.gp
    try:
        user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass
    foreground = user.GetForegroundWindow()
    work, scale = _monitor_and_dpi(native, foreground)
    width, height, margin = round(WIDTH * scale), round(HEIGHT * scale), round(MARGIN * scale)
    x, y = _place(work, width, height, margin)

    ctypes.set_last_error(0)
    mutex = kernel.CreateMutexW(None, False, "Local\\uselessMaybe.Toast")
    if not mutex:
        return False
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel.CloseHandle(mutex)
        return False

    token = ctypes.c_size_t()
    hwnd = hdc = bitmap = old_bitmap = graphics = target = None
    atom = 0
    class_name = f"uselessMaybeToast_{kernel.GetModuleHandleW(None)}"
    try:
        startup = GDIPLUS_STARTUP_INPUT(1, None, False, False)
        _check(gp.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup), None), "startup")

        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p,
                                            wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)

        def window_proc(window, msg, wparam, lparam):
            if msg == WM_MOUSEACTIVATE:
                return MA_NOACTIVATEANDEAT
            if msg == WM_NCHITTEST:
                return HTTRANSPARENT
            return user.DefWindowProcW(window, msg, wparam, lparam)

        callback = callback_type(window_proc)
        instance = kernel.GetModuleHandleW(None)
        window_class = WNDCLASSEXW()
        window_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
        window_class.lpfnWndProc = ctypes.cast(callback, ctypes.c_void_p)
        window_class.hInstance = instance
        window_class.lpszClassName = class_name
        atom = user.RegisterClassExW(ctypes.byref(window_class))
        if not atom:
            raise ctypes.WinError(ctypes.get_last_error())
        # No Tk wrapper exists. These styles are fixed at the exact instant the
        # HWND is created, before there is any possibility of visibility.
        hwnd = user.CreateWindowExW(WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW |
                                    WS_EX_LAYERED | WS_EX_TRANSPARENT,
                                    class_name, "uselessMaybe · toast", WS_POPUP,
                                    x, y, width, height, None, None, instance, None)
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        hdc = gdi.CreateCompatibleDC(None)
        if not hdc:
            raise ctypes.WinError(ctypes.get_last_error())
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height  # top-down DIB: same coordinates as GDI+
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        pixels = ctypes.c_void_p()
        bitmap = gdi.CreateDIBSection(None, ctypes.byref(info), 0,
                                       ctypes.byref(pixels), None, 0)
        if not bitmap or not pixels:
            raise ctypes.WinError(ctypes.get_last_error())
        old_bitmap = gdi.SelectObject(hdc, bitmap)
        if not old_bitmap:
            raise ctypes.WinError(ctypes.get_last_error())
        target = ctypes.c_void_p()
        _check(gp.GdipCreateBitmapFromScan0(width, height, width * 4,
                                             PIXEL_FORMAT_32BPP_PARGB, pixels,
                                             ctypes.byref(target)), "create pixel target")
        graphics = ctypes.c_void_p()
        _check(gp.GdipGetImageGraphicsContext(target, ctypes.byref(graphics)), "graphics")
        _render(native, graphics, width, height, scale, _bounded_message(message),
                Path(__file__).resolve().parents[1] / "assets")
        destination, dimensions, source = POINT(x, y), SIZE(width, height), POINT(0, 0)
        blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
        if not user.UpdateLayeredWindow(hwnd, None, ctypes.byref(destination),
                                        ctypes.byref(dimensions), hdc, ctypes.byref(source),
                                        0, ctypes.byref(blend), ULW_ALPHA):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user.SetWindowPos(hwnd, ctypes.c_void_p(-1), x, y, width, height,
                                 SWP_NOACTIVATE | SWP_SHOWWINDOW):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user.IsWindowVisible(hwnd):
            return False

        deadline = time.monotonic() + duration
        pending = MSG()
        while time.monotonic() < deadline:
            while user.PeekMessageW(ctypes.byref(pending), None, 0, 0, PM_REMOVE):
                user.TranslateMessage(ctypes.byref(pending))
                user.DispatchMessageW(ctypes.byref(pending))
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        return True
    finally:
        if hwnd: user.DestroyWindow(hwnd)
        if graphics: gp.GdipDeleteGraphics(graphics)
        if target: gp.GdipDisposeImage(target)
        if old_bitmap and hdc: gdi.SelectObject(hdc, old_bitmap)
        if bitmap: gdi.DeleteObject(bitmap)
        if hdc: gdi.DeleteDC(hdc)
        if atom: user.UnregisterClassW(class_name, kernel.GetModuleHandleW(None))
        if token.value: gp.GdiplusShutdown(token)
        kernel.CloseHandle(mutex)
