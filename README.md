# Fickle FOSS

An app for fickle giving (<https://fickle.giving>).

**Fickle giving** is the idea of, rather than committing to monthly donations to a specific project(s), you commit to monthly donations to whatever project(s) you feel like each month 💕. Fickle FOSS helps you choose by showing you which apps you use most often, and it helps you remember your generosity by giving you a place to record your donations.

**Happy giving!**

---

## Dependencies

This program (Fickle FOSS) is a GUI for viewing app usage and recording donations. You also need a separate program to record which apps are used each day. 

**Gnome** users can install the [Fickle FOSS Tracker Gnome extension](https://github.com/benopotamus/fickle-foss-tracker-gnome-extension).
Other users can install the systemd [Fickle FOSS Tracker program](https://github.com/benopotamus/fickle-foss-tracker).

### Compiling from source

To compile and install the source code, you will need the Gnome development tools `meson` and `ninja`.

---

## Automated install

Just run ``install.sh``. It will do what **Manual install** does below.

## Manual install

### 1. Compile the project with Meson

```bash
meson setup _build . --prefix="$HOME/.local"
meson compile -C _build
```

### 2. Install with Meson

```bash
meson install -C _build
```

This installs the following (all under `~/.local`):

- The `fickle-foss` executable → `~/.local/bin/fickle-foss`
- App resources and Python modules → `~/.local/share/fickle-foss/`
- The `.desktop` launcher → `~/.local/share/applications/`
- App icons → `~/.local/share/icons/hicolor/...`
- The GSettings schema → `~/.local/share/glib-2.0/schemas/`
- A D-Bus service file → `~/.local/share/dbus-1/services/`

---

## Uninstalling

If you still have the build directory from installing:

```bash
ninja -C _build uninstall
```

If you've removed the build directory, remove the installed files manually instead:

```bash
rm ~/.local/bin/fickle-foss
rm -rf ~/.local/share/fickle-foss
rm ~/.local/share/applications/giving.fickle.foss.desktop
rm ~/.local/share/metainfo/giving.fickle.foss.metainfo.xml
rm ~/.local/share/glib-2.0/schemas/giving.fickle.foss.gschema.xml
rm ~/.local/share/dbus-1/services/giving.fickle.foss.service
rm ~/.local/share/icons/hicolor/scalable/apps/giving.fickle.foss.svg
rm ~/.local/share/icons/hicolor/symbolic/apps/giving.fickle.foss-symbolic.svg
glib-compile-schemas ~/.local/share/glib-2.0/schemas
```
