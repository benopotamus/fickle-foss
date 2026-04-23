# Fickle FOSS Tracker

Records which desktop applications (those listed in your desktop menus) are
launched each day.

This is the first part in creating a fickle giving app where users can donate to FOSS apps they regularly use.

---

## Easy install

Just run install.sh

## Manual install

### 1. Copy the Python scripts to home directory

```bash
mkdir -p ~/.local/bin/fickle-foss/
mv fickle_foss_tracker.py fickle_foss_query.py ~/.local/bin/fickle-foss/
mv tracker_utils ~/.local/bin/fickle-foss/
chmod +x ~/.local/bin/fickle-foss/fickle_foss_tracker.py ~/.local/bin/fickle-foss/fickle_foss_query.py
```

### 2. Install the systemd user service

```bash
mkdir -p ~/.config/systemd/user
mv fickle-foss-tracker.service ~/.config/systemd/user/fickle-foss-tracker.service

systemctl --user daemon-reload
systemctl --user enable fickle-foss-tracker.service
systemctl --user start fickle-foss-tracker.service
```

### 3. Verify it's running

```bash
systemctl --user status fickle-foss-tracker
```

You should see `Active: active (running)`. 

The database is automatically created at:

```
~/.local/share/fickle_foss/fickle_foss.db
```

---

## Querying the data

If you did a manual install, use the full script path - ``python3 ~/.local/bin/fickle-foss/fickle_foss_query.py`` - instead of the ``fickle-foss-query`` command (added automatically by ``install.sh``.

```bash
# Show apps used in last 30 days (ordered by number of days used)
fickle-foss-query

# Apps used today
fickle-foss-query --today

# On a specific date
fickle-foss-query --date 2024-03-15

# Last 7 days
fickle-foss-query --week

# Last 30 days
fickle-foss-query --month

# All recorded data
fickle-foss-query --alltime
```

Or query the SQLite database directly:

```bash
sqlite3 ~/.local/share/fickle_foss/fickle_foss.db \
  "SELECT date, app_name, COUNT(*) FROM app_launches GROUP BY date, app_name ORDER BY date DESC;"
```
---

## Stopping / uninstalling

```bash
# Stop and disable
systemctl --user stop fickle-foss-tracker
systemctl --user disable fickle-foss-tracker

# Remove files
rm ~/.config/systemd/user/fickle-foss-tracker.service
rm -rf ~/.local/bin/fickle-foss

# Optionally remove the database
rm ~/.local/share/fickle_foss

# If installed with install.sh, remove fickle-foss command as well
rm ~/.local/bin/fickle-foss-query
```