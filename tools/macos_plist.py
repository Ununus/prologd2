"""Writes the macOS bundle metadata PyInstaller leaves out (task_119).

    python tools/macos_plist.py dist/PrologD.app/Contents/Info.plist 2.6.1

PyInstaller fills in the executable, the identifier and the icon; the version,
the deployment floor and the document type are ours.  The file is a binary or
XML plist, so it is edited with `plistlib` rather than by string replacement.
The tool runs on any Python (not only macOS), which is how the workflow checks
it without a Mac.
"""

from __future__ import annotations

import pathlib
import plistlib
import sys

#: Qt 6.12, the version PySide6 6.12 ships, targets macOS 14.4 and newer.
MINIMUM_SYSTEM = "14.4"

#: The exported UTI and the document type that make Finder offer the app for `.pld`.
PROGRAM_UTI = "com.csu.prologd.program"
DOCUMENT_NAME = "Программа Пролог-Д"


def update(path: pathlib.Path, version: str) -> None:
    with path.open("rb") as stream:
        data = plistlib.load(stream)
    data["CFBundleShortVersionString"] = version
    data["CFBundleVersion"] = version
    data["LSMinimumSystemVersion"] = MINIMUM_SYSTEM
    data["NSHighResolutionCapable"] = True
    data["LSApplicationCategoryType"] = "public.app-category.education"
    data["UTExportedTypeDeclarations"] = [
        {
            "UTTypeIdentifier": PROGRAM_UTI,
            "UTTypeDescription": DOCUMENT_NAME,
            "UTTypeConformsTo": ["public.plain-text"],
            "UTTypeTagSpecification": {"public.filename-extension": ["pld"]},
        }
    ]
    data["CFBundleDocumentTypes"] = [
        {
            "CFBundleTypeName": DOCUMENT_NAME,
            "CFBundleTypeRole": "Editor",
            "LSItemContentTypes": [PROGRAM_UTI],
        }
    ]
    with path.open("wb") as stream:
        plistlib.dump(data, stream, sort_keys=False)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: tools/macos_plist.py Info.plist VERSION")
        return 2
    path = pathlib.Path(argv[0])
    if not path.is_file():
        print(f"no {path}")
        return 1
    update(path, argv[1])
    print(f"updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
