"""Limit vault file access to the current Windows user."""

import csv
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import subprocess


def restrict_access(path: Path) -> None:
    path = Path(path)
    if os.name != "nt":
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
        return
    try:
        result = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise OSError("Could not identify the current Windows user for vault permissions.") from exc
    rows = list(csv.reader(result.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not re.fullmatch(r"S-1-\d+(?:-\d+)+", rows[0][1]):
        raise OSError("Could not identify the current Windows user for vault permissions.")
    sid = rows[0][1]
    # Replace the entire DACL in one call. Removing inheritance alone would
    # leave preexisting explicit grants to other accounts in place.
    advapi = ctypes.WinDLL("Advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("Kernel32", use_last_error=True)
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    convert.restype = wintypes.BOOL
    get_dacl = advapi.GetSecurityDescriptorDacl
    get_dacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
                         ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
    get_dacl.restype = wintypes.BOOL
    set_info = advapi.SetNamedSecurityInfoW
    set_info.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    set_info.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p

    inheritance = "OICI" if path.is_dir() else ""
    sddl = f"D:P(A;{inheritance};FA;;;{sid})"
    descriptor = ctypes.c_void_p()
    if not convert(sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        dacl = ctypes.c_void_p()
        if not get_dacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)) or not present.value:
            raise OSError("Could not construct a private Windows vault ACL.")
        # SE_FILE_OBJECT=1; DACL_SECURITY_INFORMATION=4;
        # PROTECTED_DACL_SECURITY_INFORMATION=0x80000000.
        result = set_info(str(path.resolve()), 1, 0x80000004, None, None, dacl, None)
        if result:
            raise ctypes.WinError(result)
    finally:
        kernel.LocalFree(descriptor)
