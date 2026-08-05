#!/bin/bash
set -e

PREFIX="$HOME/.local"
BUILD_DIR_NAME="_fickle_foss_build"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/$BUILD_DIR_NAME"

# ── Helpers ────────────────────────────────────────────────────────────────────

green()  { echo -e "\033[0;32m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }

# ── Check we're not being run as root ─────────────────────────────────────────

if [ "$EUID" -eq 0 ]; then
    red "Do not run this script as root. Fickle FOSS installs for your user only."
    exit 1
fi

# ── Check required build tools ───────────────────────────────────────────────

missing_tool=false

check_tool() {
    if ! command -v "$1" &> /dev/null; then
        red "Missing required tool: $1"
        yellow "  $2"
        missing_tool=true
    fi
}

check_tool "python3"                "Install python3 using your distro's package manager."
check_tool "meson"                  "Install with: pip install --user meson   (or your distro's 'meson' package)"
check_tool "ninja"                  "Install with your distro's 'ninja-build' or 'ninja' package."
check_tool "msgfmt"                 "Install your distro's 'gettext' package."
check_tool "update-desktop-database" "Install your distro's 'desktop-file-utils' package."
check_tool "glib-compile-schemas"   "Install your distro's 'glib2' / 'libglib2.0-dev' / 'libglib2.0-bin' package."

if [ "$missing_tool" = true ]; then
    red "Please install the missing tools above and re-run this script."
    exit 1
fi

# ── Check for GTK4 / Libadwaita python bindings ──────────────────────────────

if ! python3 -c "
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
" &> /dev/null; then
    red "Python GTK4/Libadwaita bindings not found."
    exit 1
fi

# ── Configure and build ───────────────────────────────────────────────────────

green "Configuring build (prefix: $PREFIX)..."
if [ -d "$BUILD_DIR" ]; then
    meson setup --reconfigure "$BUILD_DIR" "$SCRIPT_DIR" --prefix="$PREFIX"
else
    meson setup "$BUILD_DIR" "$SCRIPT_DIR" --prefix="$PREFIX"
fi

green "Building..."
meson compile -C "$BUILD_DIR"

# ── Install ────────────────────────────────────────────────────────────────────

green "Installing to $PREFIX..."
meson install -C "$BUILD_DIR"

# ── Add ~/.local/bin to $PATH if needed ──────────────────────────────────────

LOCAL_BIN="$HOME/.local/bin"
SHELL_RC=""

if [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bashrc"
elif [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "$LOCAL_BIN" "$SHELL_RC" 2>/dev/null && ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
        yellow "Adding $LOCAL_BIN to PATH in $SHELL_RC..."
        echo "" >> "$SHELL_RC"
        echo "# Added by Fickle FOSS installer" >> "$SHELL_RC"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
        yellow "Run 'source $SHELL_RC' or open a new terminal for the PATH change to take effect."
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────

green ""
green "Fickle FOSS installed successfully."
green "  Binary:  $PREFIX/bin/fickle-foss"
green "  Data:    $PREFIX/share/fickle-foss/"
green "  Build:   $BUILD_DIR"
echo ""
echo "Launch from the GNOME Overview by searching 'Fickle FOSS'."
echo ""
yellow "Note: Fickle FOSS reads its data from fickle-foss-tracker's database."
yellow "If you haven't installed fickle-foss-tracker yet, install that first"
yellow "(or the app will report that no database was found)."
