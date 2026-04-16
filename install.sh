#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/bin/fickle-foss"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="fickle-foss-tracker.service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Helpers ────────────────────────────────────────────────────────────────────

green()  { echo -e "\033[0;32m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }

# ── Check we're not being run as root ─────────────────────────────────────────

if [ "$EUID" -eq 0 ]; then
    red "Do not run this script as root. Fickle FOSS installs for your user only."
    exit 1
fi

# ── Copy files ────────────────────────────────────────────────────────────────

green "Installing files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copy all Python files
cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/fickle_foss_tracker.py"
chmod +x "$INSTALL_DIR/fickle_foss_query.py"

# Copy tracker_utils directory if it exists
if [ -d "$SCRIPT_DIR/tracker_utils" ]; then
    cp -r "$SCRIPT_DIR/tracker_utils" "$INSTALL_DIR/"
fi

# Install the fickle-foss-query command wrapper into ~/.local/bin
green "Installing fickle-foss-query command..."
cat > "$HOME/.local/bin/fickle-foss-query" << 'EOF'
#!/bin/bash
exec "$(dirname "$(realpath "$0")")/fickle-foss/fickle_foss_query.py" "$@"
EOF
chmod +x "$HOME/.local/bin/fickle-foss-query"

# ── Install systemd service ───────────────────────────────────────────────────

green "Installing systemd service..."
mkdir -p "$SERVICE_DIR"
cp "$SCRIPT_DIR/$SERVICE_NAME" "$SERVICE_DIR/$SERVICE_NAME"

systemctl --user daemon-reload

# If already running (reinstall/update), restart it; otherwise enable and start
if systemctl --user is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    yellow "Service already installed — restarting with updated files..."
    systemctl --user restart "$SERVICE_NAME"
else
    systemctl --user enable --now "$SERVICE_NAME"
fi

# ── Add ~/.local/bin to $PATH if needed ──────────────────────────────────────

LOCAL_BIN="$HOME/.local/bin"
SHELL_RC=""

if [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bashrc"
elif [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
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
green "  Files:   $INSTALL_DIR"
green "  Service: $SERVICE_DIR/$SERVICE_NAME"
green "  Data:    $HOME/.local/share/fickle_foss/"
echo ""
echo "Check service status:  systemctl --user status $SERVICE_NAME"
echo "Query your app usage:  fickle-foss-query"
echo "                   or: fickle-foss-query --stats"
