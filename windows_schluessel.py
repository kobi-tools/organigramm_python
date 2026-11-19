"""Verwaltet Veröffentlichungsschlüssel im Windows-Anmeldeinformationsspeicher."""

import ctypes
import hashlib
import os
from ctypes import wintypes
from urllib.parse import urlsplit


VERFUEGBAR = os.name == "nt"
_GENERIC = 1
_LOCAL_MACHINE = 2
_NOT_FOUND = 1168


class _Anmeldeinformation(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


if VERFUEGBAR:
    _api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    _pointer = ctypes.POINTER(_Anmeldeinformation)
    _api.CredReadW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_pointer))
    _api.CredReadW.restype = wintypes.BOOL
    _api.CredWriteW.argtypes = (_pointer, wintypes.DWORD)
    _api.CredWriteW.restype = wintypes.BOOL
    _api.CredDeleteW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
    _api.CredDeleteW.restype = wintypes.BOOL
    _api.CredFree.argtypes = (ctypes.c_void_p,)
    _api.CredFree.restype = None


def _zielname(adresse):
    url = urlsplit(adresse)
    # Der Pfad kann Groß-/Kleinschreibung unterscheiden, der Windows-Zielname nicht.
    endpunkt = f"{url.hostname}:{url.port or 443}{url.path}"
    digest = hashlib.sha256(endpunkt.encode("utf-8")).hexdigest()
    return f"Ordner-Organigramm/{url.hostname}/{digest}"


def lesen(adresse):
    if not VERFUEGBAR:
        return ""
    eintrag = _pointer()
    if not _api.CredReadW(_zielname(adresse), _GENERIC, 0, ctypes.byref(eintrag)):
        fehler = ctypes.get_last_error()
        if fehler == _NOT_FOUND:
            return ""
        raise ctypes.WinError(fehler)
    try:
        daten = eintrag.contents
        return ctypes.string_at(daten.CredentialBlob, daten.CredentialBlobSize).decode("utf-8")
    finally:
        _api.CredFree(eintrag)


def speichern(adresse, schluessel):
    if not VERFUEGBAR:
        return
    name = _zielname(adresse)
    if not schluessel:
        if not _api.CredDeleteW(name, _GENERIC, 0):
            fehler = ctypes.get_last_error()
            if fehler != _NOT_FOUND:
                raise ctypes.WinError(fehler)
        return
    daten = schluessel.encode("utf-8")
    puffer = ctypes.create_string_buffer(daten)
    eintrag = _Anmeldeinformation(
        Type=_GENERIC,
        TargetName=name,
        CredentialBlobSize=len(daten),
        CredentialBlob=ctypes.addressof(puffer),
        Persist=_LOCAL_MACHINE,
        UserName="Ordner-Organigramm",
    )
    if not _api.CredWriteW(ctypes.byref(eintrag), 0):
        raise ctypes.WinError(ctypes.get_last_error())
