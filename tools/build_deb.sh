#!/usr/bin/env bash
# Builds the Debian package of the window and both engines (task_118).
#
#   tools/build_deb.sh                 engines -> tests -> docs -> freeze -> .deb
#   tools/build_deb.sh --skip-tests    quick repack; the build tree is reused
#   tools/build_deb.sh --skip-docs     reuse the PDFs already in doc/
#   tools/build_deb.sh --skip-freeze   reuse dist/prologd-gui
#   tools/build_deb.sh --no-trim       keep the Qt files the freeze produced
#
# The package mirrors the portable Windows folder, with Debian's own places: the
# engines, the frozen window, doc/*.pdf, examples and stdlib live together in
# /opt/prologd, because the engine searches stdlib beside itself and the window
# looks for the engines beside itself.  /usr carries the command, the menu entry,
# the MIME type, the hicolor icons and the package's copyright.
#
# Every message here is ASCII, like the Windows twins: one style for the
# packaging scripts, and no locale can mangle it.  The files the package installs
# are UTF-8 where they need to be (the desktop entry and the MIME XML); they come
# from installer/linux/.
#
# Needs: cmake, ninja, dpkg-deb, typst (unless --skip-docs), PyInstaller in the
# build Python (unless --skip-freeze), and the generated icons under
# installer/linux/icons (tools/make_png_icons.py).
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

BUILD="$ROOT/build/linux-release"
DIST="$ROOT/dist"
TREE="$ROOT/build/deb-tree"
PRESET="linux-release"
PYTHON=${PYTHON:-$ROOT/.venv/bin/python}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 2)}
DOCUMENTS=(help technical prologd-diff gui lessons library)

#: Qt pieces the window never loads, relative to /opt/prologd (task_118).  Freezing
#: keeps them whatever `--exclude-module` says: PySide6 ships its Qt libraries as
#: data of the whole package, which was measured on Windows too (build_portable.ps1,
#: `$trimmedFiles`).  The `libQt6*.so.6` names without a folder are the loader's
#: symlinks to the files under `PySide6/Qt/lib`, and the four plugins are only
#: reachable through the libraries above (`libqvnc` needs Qt6Network).
TRIMMED=(
    _internal/libQt6Network.so.6
    _internal/libQt6Pdf.so.6
    _internal/libQt6Qml.so.6
    _internal/libQt6QmlMeta.so.6
    _internal/libQt6QmlModels.so.6
    _internal/libQt6QmlWorkerScript.so.6
    _internal/libQt6Quick.so.6
    _internal/libQt6VirtualKeyboard.so.6
    _internal/libQt6VirtualKeyboardQml.so.6
    _internal/PySide6/Qt/lib/libQt6Network.so.6
    _internal/PySide6/Qt/lib/libQt6Pdf.so.6
    _internal/PySide6/Qt/lib/libQt6Qml.so.6
    _internal/PySide6/Qt/lib/libQt6QmlMeta.so.6
    _internal/PySide6/Qt/lib/libQt6QmlModels.so.6
    _internal/PySide6/Qt/lib/libQt6QmlWorkerScript.so.6
    _internal/PySide6/Qt/lib/libQt6Quick.so.6
    _internal/PySide6/Qt/lib/libQt6VirtualKeyboard.so.6
    _internal/PySide6/Qt/lib/libQt6VirtualKeyboardQml.so.6
    _internal/PySide6/Qt/plugins/generic/libqtuiotouchplugin.so
    _internal/PySide6/Qt/plugins/imageformats/libqpdf.so
    _internal/PySide6/Qt/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so
    _internal/PySide6/Qt/plugins/platforms/libqvnc.so
)

skip_tests=0
skip_docs=0
skip_freeze=0
skip_trim=0

show_help() {
    sed -n '2,23p' "$0"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-tests) skip_tests=1 ;;
        --skip-docs) skip_docs=1 ;;
        --skip-freeze) skip_freeze=1 ;;
        --no-trim) skip_trim=1 ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

step() { printf '\n=== %s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "missing tool: $1"; }

step '1/8 Check the tools'
need cmake
need ninja
need dpkg-deb
need dpkg
need gzip
need md5sum
need find
need du
need timeout
[ -x "$PYTHON" ] || fail "no Python at $PYTHON (set PYTHON or create .venv)"
if [ "$skip_docs" -eq 0 ]; then
    need typst
fi
if [ "$skip_freeze" -eq 0 ]; then
    "$PYTHON" -m PyInstaller --version >/dev/null 2>&1 || fail \
        "PyInstaller is not installed in $PYTHON: $PYTHON -m pip install -r src/gui/requirements-build.txt"
fi
for icon in installer/linux/icons/hicolor/16x16/apps/prologd.png \
            installer/linux/icons/hicolor/256x256/mimetypes/application-x-prologd.png; do
    [ -f "$icon" ] || fail "missing $icon (run $PYTHON tools/make_png_icons.py)"
done
echo "python : $PYTHON"

step '2/8 Build the engines'
cmake --preset "$PRESET" -DBUILD_WITH_PROLOGD=ON
cmake --build "$BUILD" -j "$JOBS"
PROLOGU="$BUILD/src/cli/prologu"
PROLOGD="$BUILD/src/cli/prologd"
[ -x "$PROLOGU" ] || fail "the build left no $PROLOGU"
[ -x "$PROLOGD" ] || fail "the build left no $PROLOGD (BUILD_WITH_PROLOGD=ON?)"

VERSION=$("$PROLOGU" --version | head -n 1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || true)
[ -n "$VERSION" ] || fail "prologu --version printed no version number"
ARCH=$(dpkg --print-architecture)
GLIBC=$(ldd --version | head -n 1 | grep -oE '[0-9]+\.[0-9]+$' | head -n 1 || true)
[ -n "$GLIBC" ] || fail "could not read the glibc version from ldd --version"
echo "version : $VERSION"
echo "arch    : $ARCH (glibc >= $GLIBC)"

step '3/8 Run the tests'
if [ "$skip_tests" -eq 0 ]; then
    ctest --test-dir "$BUILD" -j "$JOBS" --output-on-failure
else
    echo 'skipped (--skip-tests)'
fi

step '4/8 Build the manuals'
if [ "$skip_docs" -eq 0 ]; then
    cmake --build "$BUILD" --target docs
else
    echo 'skipped (--skip-docs)'
fi
for name in "${DOCUMENTS[@]}"; do
    [ -f "doc/$name.pdf" ] || fail "doc/$name.pdf is missing (the docs target failed?)"
done
[ -f doc/builtins.json ] || fail 'doc/builtins.json is missing (F1 reads it)'
echo "documents: ${#DOCUMENTS[@]} PDFs and builtins.json"

step '5/8 Freeze the window (PyInstaller --onedir)'
GUI_DIST="$DIST/prologd-gui"
if [ "$skip_freeze" -eq 0 ]; then
    freeze=( -m PyInstaller --noconfirm --clean --onedir --windowed
             --name prologd-gui
             --add-data 'src/gui/assets:assets'
             --paths src/gui
             --workpath build/pyinstaller
             --distpath dist )
    for module in PySide6.QtQml PySide6.QtQuick PySide6.QtQuickWidgets \
                  PySide6.QtQuickControls2 PySide6.QtPdf PySide6.QtPdfWidgets \
                  PySide6.QtVirtualKeyboard PySide6.QtNetwork PySide6.QtNetworkAuth; do
        freeze+=( --exclude-module "$module" )
    done
    "$PYTHON" "${freeze[@]}" src/gui/main.py
else
    echo 'skipped (--skip-freeze), reusing dist/prologd-gui'
fi
[ -x "$GUI_DIST/prologd-gui" ] || fail "the window was not frozen: $GUI_DIST/prologd-gui"

step '6/8 Lay out the package tree'
rm -rf "$TREE"
mkdir -p "$TREE/opt/prologd/doc" "$TREE/usr/bin" \
         "$TREE/usr/share/applications" "$TREE/usr/share/mime/packages" \
         "$TREE/usr/share/icons/hicolor" "$TREE/usr/share/doc/prologd" \
         "$TREE/usr/share/lintian/overrides" "$TREE/DEBIAN"
cp -a "$GUI_DIST/." "$TREE/opt/prologd/"

# The freeze keeps Qt pieces the window never loads; dropping them takes about 23
# MiB out of the package (measured on the 2.6.1 `.deb`).  The offscreen start below
# is what says the window still runs without them.
if [ "$skip_trim" -eq 0 ]; then
    freed=0
    for relative in "${TRIMMED[@]}"; do
        target="$TREE/opt/prologd/$relative"
        if [ ! -e "$target" ] && [ ! -L "$target" ]; then
            continue
        fi
        size=$(du -sk -- "$target" | cut -f1)
        rm -rf -- "$target"
        freed=$((freed + size))
        printf 'trimmed : %s (%s KiB)\n' "$relative" "$size"
    done
    printf 'trimmed : %s KiB of Qt files no window of ours loads\n' "$freed"
else
    echo 'trimmed : skipped (--no-trim)'
fi

install -m 0755 "$PROLOGU" "$TREE/opt/prologd/prologu"
install -m 0755 "$PROLOGD" "$TREE/opt/prologd/prologd"
for name in "${DOCUMENTS[@]}"; do
    install -m 0644 "doc/$name.pdf" "$TREE/opt/prologd/doc/$name.pdf"
done
install -m 0644 doc/builtins.json "$TREE/opt/prologd/doc/builtins.json"
cp -a examples "$TREE/opt/prologd/examples"
rm -rf "$TREE/opt/prologd/examples/lessons/_old"
cp -a stdlib "$TREE/opt/prologd/stdlib"
install -m 0755 installer/linux/prologd-gui "$TREE/usr/bin/prologd-gui"
install -m 0644 installer/linux/prologd.desktop "$TREE/usr/share/applications/prologd.desktop"
install -m 0644 installer/linux/prologd.xml "$TREE/usr/share/mime/packages/prologd.xml"
cp -a installer/linux/icons/hicolor/. "$TREE/usr/share/icons/hicolor/"

install -m 0644 installer/linux/copyright "$TREE/usr/share/doc/prologd/copyright"
install -m 0644 installer/linux/lintian-overrides "$TREE/usr/share/lintian/overrides/prologd"
{
    printf '%s (%s) unstable; urgency=medium\n\n' prologd "$VERSION"
    printf '  * Package built from the %s sources.\n\n' "$VERSION"
    printf ' -- Aleksei Voronin <74496235+Ununus@users.noreply.github.com>  %s\n' "$(date -R)"
} | gzip -9n > "$TREE/usr/share/doc/prologd/changelog.gz"
# The source tree is group-writable; an installed program is not.  Normalise
# every file first, then restore the executables (lintian counts every other
# mode as non-standard).
find "$TREE" -type d -exec chmod 0755 {} +
find "$TREE" -type f -exec chmod 0644 {} +
chmod 0755 "$TREE/opt/prologd/prologu" "$TREE/opt/prologd/prologd" \
           "$TREE/opt/prologd/prologd-gui" "$TREE/usr/bin/prologd-gui"

step '7/8 Check the tree and the frozen window'
[ -x "$TREE/opt/prologd/prologu" ] || fail 'the tree has no prologu'
[ -x "$TREE/opt/prologd/prologd" ] || fail 'the tree has no prologd'
[ -x "$TREE/usr/bin/prologd-gui" ] || fail 'the tree has no prologd-gui command'
[ -f "$TREE/usr/share/icons/hicolor/48x48/apps/prologd.png" ] || fail 'the hicolor icons were not copied'
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$TREE/usr/share/applications/prologd.desktop"
fi
if command -v xmllint >/dev/null 2>&1; then
    xmllint --noout "$TREE/usr/share/mime/packages/prologd.xml"
fi
"$TREE/opt/prologd/prologu" --version >/dev/null
legacy_keywords=$(cd "$TREE/opt/prologd" && ./prologd --list-keywords | wc -l)
[ "$legacy_keywords" -ge 40 ] || fail "prologd lists only $legacy_keywords keyword lines"
(cd "$TREE/opt/prologd" && ./prologu -s examples/lessons/lesson_01.pld >/dev/null)
status=0
QT_QPA_PLATFORM=offscreen timeout 8 "$TREE/opt/prologd/prologd-gui" >/dev/null 2>&1 || status=$?
if [ "$status" -ne 124 ]; then
    fail "the frozen window did not stay up (exit $status)"
fi
rm -f "$TREE/opt/prologd/gui.ini"
if [ "$skip_trim" -eq 0 ]; then
    # A trimmed library that something still names would be found on this machine
    # (system Qt) and nowhere on a user's: ask every remaining binary what it
    # needs, and refuse a name that was taken away.
    trimmed_names=$(printf '%s\n' "${TRIMMED[@]}" | sed -e 's|.*/||' | sort -u)
    still_wanted=$(find "$TREE/opt/prologd" -type f \( -name '*.so*' -o -name 'prologd-gui' \) \
        -print0 | xargs -0 -r readelf -d 2>/dev/null |
        grep -oE 'libQt6[A-Za-z0-9]+\.so[0-9.]*' | sort -u |
        while read -r name; do
            if printf '%s\n' "$trimmed_names" | grep -qx -- "$name"; then
                echo "$name"
            fi
        done)
    [ -z "$still_wanted" ] || fail "the package still asks for the trimmed $still_wanted"
fi
echo "engines : prologu $VERSION, prologd $legacy_keywords keyword lines"
echo 'window  : the frozen prologd-gui starts offscreen'

step '8/8 Build the .deb'
INSTALLED_SIZE=$(du -sk "$TREE" | awk '{print $1}')
sed -e "s|@VERSION@|$VERSION|g" \
    -e "s|@ARCH@|$ARCH|g" \
    -e "s|@GLIBC@|$GLIBC|g" \
    -e "s|@SIZE@|$INSTALLED_SIZE|g" \
    installer/linux/control > "$TREE/DEBIAN/control"
install -m 0755 installer/linux/postinst "$TREE/DEBIAN/postinst"
install -m 0755 installer/linux/postrm "$TREE/DEBIAN/postrm"
(
    cd "$TREE"
    find . -path ./DEBIAN -prune -o -type f -print0 |
        sed -z 's|^\./||' |
        LC_ALL=C sort -z |
        xargs -0 md5sum
) > "$TREE/DEBIAN/md5sums"
mkdir -p "$DIST"
DEB="$DIST/prologd_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$TREE" "$DEB" >/dev/null
SIZE=$(du -h "$DEB" | awk '{print $1}')
echo "package : $DEB ($SIZE)"
printf '\nLeft for a person: install it with sudo apt install %s, start it\n' "$DEB"
printf 'from the menu, open a .pld with "Open With", then remove it and check that\n'
printf '/opt and /usr are clean.  The default .pld handler is never changed.\n'
