import ctypes
import ctypes.wintypes
from pathlib import Path


class _VS_FIXEDFILEINFO(ctypes.Structure):
    _fields_ = [
        ("dwSignature",        ctypes.c_uint32),
        ("dwStrucVersion",     ctypes.c_uint32),
        ("dwFileVersionMS",    ctypes.c_uint32),
        ("dwFileVersionLS",    ctypes.c_uint32),
        ("dwProductVersionMS", ctypes.c_uint32),
        ("dwProductVersionLS", ctypes.c_uint32),
        ("dwFileFlagsMask",    ctypes.c_uint32),
        ("dwFileFlags",        ctypes.c_uint32),
        ("dwFileOS",           ctypes.c_uint32),
        ("dwFileType",         ctypes.c_uint32),
        ("dwFileSubtype",      ctypes.c_uint32),
        ("dwFileDateMS",       ctypes.c_uint32),
        ("dwFileDateLS",       ctypes.c_uint32),
    ]


def get_file_version(path: Path) -> str | None:
    """Return the embedded FileVersion of a Windows PE file, or None on failure."""
    try:
        s = str(path)
        size = ctypes.windll.version.GetFileVersionInfoSizeW(s, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(s, 0, size, buf):
            return None
        p_info = ctypes.c_void_p()
        n_info = ctypes.c_uint()
        if not ctypes.windll.version.VerQueryValueW(
            buf, "\\", ctypes.byref(p_info), ctypes.byref(n_info)
        ):
            return None
        info = ctypes.cast(p_info, ctypes.POINTER(_VS_FIXEDFILEINFO)).contents
        ms = info.dwFileVersionMS
        ls = info.dwFileVersionLS
        major = ms >> 16
        minor = ms & 0xFFFF
        patch = ls >> 16
        build = ls & 0xFFFF
        return f"{major}.{minor}.{patch}.{build}"
    except Exception:
        return None


def _parse_version(tag: str) -> tuple[int, ...]:
    clean = tag.lstrip("vV")
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts) or (0,)


def format_version(tag: str) -> str:
    """Strip v-prefix and normalise to exactly 4 numeric parts (e.g. '1.2.3.0')."""
    parts = _parse_version(tag)
    padded = (parts + (0, 0, 0, 0))[:4]
    return ".".join(str(p) for p in padded)


def compare_versions(a: str, b: str) -> int:
    """Return -1 if a < b, 0 if equal, 1 if a > b."""
    av = _parse_version(a)
    bv = _parse_version(b)
    length = max(len(av), len(bv))
    av += (0,) * (length - len(av))
    bv += (0,) * (length - len(bv))
    if av < bv:
        return -1
    if av > bv:
        return 1
    return 0
