"""What a Windows executable imports, and whether a package carries it.

    python tools/check_dependencies.py dist/prologd-2.0.0-win64

The build machine is the wrong place to ask "does the package have everything?":
it has the Visual C++ runtime in `System32` (Visual Studio installed), so a
forgotten DLL would not show up here.  This script asks the PE import table
instead, and for every name decides where it should come from (task_61 §7.3):

* `api-ms-win-*` - an **API set**, not a file: the loader resolves it through the
  OS schema (`apisetschema.dll`), and on Windows 10 and newer the Universal CRT it
  stands for is part of the system.  Nothing to ship;
* a short list of system DLLs below - present on every Windows;
* anything else - a file with that name has to be somewhere in the package
  (`vcruntime140.dll`, and inside a PyInstaller folder the Qt DLLs of `_internal`).

A name that fits none of the three is printed as a **suspect** and the exit code
becomes 1, because that is the shape of a package that will not start on a machine
that has nothing installed.
"""

from __future__ import annotations

import pathlib
import struct
import sys

#: Present on every supported Windows (10 1903+), by definition of the system.
SYSTEM_DLLS = {
    "advapi32.dll",
    "authz.dll",
    "avrt.dll",
    "bcrypt.dll",
    "cabinet.dll",
    "cfgv2.dll",
    "comctl32.dll",
    "comdlg32.dll",
    "crypt32.dll",
    "d2d1.dll",
    "d3d11.dll",
    "d3d12.dll",
    "d3d9.dll",
    "dcomp.dll",
    "dnsapi.dll",
    "dwmapi.dll",
    "dwrite.dll",
    "dxgi.dll",
    "dxva2.dll",
    "gdi32.dll",
    "gdiplus.dll",
    "icu.dll",
    "icuin.dll",
    "icuuc.dll",
    "imagehlp.dll",
    "imm32.dll",
    "iphlpapi.dll",
    "kernel32.dll",
    "mf.dll",
    "mfplat.dll",
    "mfreadwrite.dll",
    "mpr.dll",
    "msimg32.dll",
    "mswsock.dll",
    "ncrypt.dll",
    "netapi32.dll",
    "ntdll.dll",
    "odbc32.dll",
    "ole32.dll",
    "oleaut32.dll",
    "opengl32.dll",
    "powrprof.dll",
    "propsys.dll",
    "psapi.dll",
    "rpcrt4.dll",
    "secur32.dll",
    "setupapi.dll",
    "shell32.dll",
    "shlwapi.dll",
    "uiautomationcore.dll",
    "user32.dll",
    "userenv.dll",
    "usp10.dll",
    "uxtheme.dll",
    "version.dll",
    "wer.dll",
    "windowscodecs.dll",
    "winhttp.dll",
    "winmm.dll",
    "winspool.drv",
    "ws2_32.dll",
    "wtsapi32.dll",
}

#: Checked on this machine (Windows 11 26200) while writing the script: every name
#: above is a file of `System32` there.  `icu.dll`, `icuuc.dll` and `icuin.dll` are
#: the ICU that Windows 10 ships; `d2d1`/`dwrite`/`d3d12` and `uiautomationcore`
#: arrive with Qt's Direct2D, DirectWrite and accessibility backends.


def imports(path: pathlib.Path) -> list[str]:
    """The DLL names the image lists in its import directory, in file order."""
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"{path.name} is not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError(f"{path.name} has no PE signature")
    _, sections_count, _, _, _, optional_size, _ = struct.unpack_from("<HHIIIHH", data, pe_offset + 4)
    optional = pe_offset + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    # The data directories sit after the standard fields: 96 bytes for PE32,
    # 112 for PE32+.  Directory 1 is the import table.
    directories = optional + (112 if magic == 0x20B else 96)
    import_rva, _ = struct.unpack_from("<II", data, directories + 8)
    if import_rva == 0:
        # `python3.dll` is such a stub: a forwarder with no imports of its own.
        return []

    sections = []
    table = optional + optional_size
    for index in range(sections_count):
        offset = table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

    def file_offset(rva: int) -> int:
        for virtual_address, size, raw_pointer in sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_pointer + (rva - virtual_address)
        raise ValueError(f"RVA {rva:#x} is outside every section")

    names: list[str] = []
    cursor = file_offset(import_rva)
    while True:
        lookup, _, _, name_rva, first_thunk = struct.unpack_from("<IIIII", data, cursor)
        if not (lookup or name_rva or first_thunk):
            break
        start = file_offset(name_rva)
        names.append(data[start : data.index(b"\0", start)].decode("ascii", "replace"))
        cursor += 20
    return names


def carried(package: pathlib.Path) -> dict[str, str]:
    """Every file name in the package, mapped to its path relative to the root."""
    found: dict[str, str] = {}
    for item in package.rglob("*"):
        if item.is_file():
            found.setdefault(item.name.lower(), str(item.relative_to(package)))
    return found


def check(package: pathlib.Path) -> int:
    present = carried(package)
    executables = sorted(
        [item for item in package.rglob("*.exe")] + [item for item in package.rglob("*.dll")]
    )
    suspects: list[str] = []
    for image in executables:
        try:
            names = imports(image)
        except ValueError as error:
            print(f"?? {image.relative_to(package)}: {error}")
            continue
        sets = [name for name in names if name.lower().startswith("api-ms-win-")]
        system = [name for name in names if name.lower() in SYSTEM_DLLS]
        shipped = [name for name in names if name.lower() in present]
        # An API set that is *also* a file of the package (PyInstaller brings
        # `ucrtbase.dll` along) counts as carried, which is what it is.
        other = [name for name in names if name not in sets + system + shipped]
        print(
            f"{str(image.relative_to(package)):>44}: {len(names):2} imports — "
            f"{len(sets)} api-sets, {len(system)} system, {len(shipped)} in the package"
            + (f", {len(other)} SUSPECTS" if other else "")
        )
        suspects += [f"{image.name} -> {name}" for name in other]
    if suspects:
        print("\nsuspects (nothing in the package, not a known system DLL):")
        for entry in suspects:
            print(f"  {entry}")
        return 1
    print("\nevery non-system import is a file of the package")
    return 0


def main(argv: list[str]) -> int:
    package = pathlib.Path(argv[1] if len(argv) > 1 else "dist/prologd-2.1.0-win64")
    if not package.is_dir():
        print(f"not a folder: {package}")
        return 2
    print(f"package: {package}")
    return check(package)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
