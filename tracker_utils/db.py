import os
import sqlite3
from datetime import datetime


def init_db(db_path):
	"""
	Creates the database and table if they don't already exist.
	Returns a connection object.

	Fields
		date        -- YYYY-MM-DD
		launched_at -- ISO-8601 timestamp
		app_name    -- friendly name (from .desktop file)
		executable  -- process comm name
	"""
	os.makedirs(os.path.dirname(db_path), exist_ok=True)
	conn = sqlite3.connect(db_path)
	conn.execute("""
		CREATE TABLE IF NOT EXISTS app_launches (
			id          INTEGER PRIMARY KEY AUTOINCREMENT,
			date        TEXT    NOT NULL,
			app_name    TEXT    NOT NULL,
			comm        TEXT    NOT NULL,
			pid         TEXT    NOT NULL,
			cmdline     TEXT    NOT NULL
		)
	""")
	conn.execute("""
		CREATE UNIQUE INDEX IF NOT EXISTS idx_date_app
		ON app_launches(date, app_name)
	""")
	conn.commit()
	return conn


def log_app(conn, app):
	"""
	Records that an app was run today - or ignores if already recorded.
	The unique index on (date, app_name) means duplicate inserts are silently ignored.
	"""
	date = datetime.now().strftime("%Y-%m-%d")
	conn.execute("""
		INSERT OR IGNORE INTO app_launches (date, app_name, comm, pid, cmdline)
		VALUES (?, ?, ?, ?, ?)
	""", (
		date,
		app["app_name"],
		app["comm"],
		app["pid"],
		" ".join(app["cmdline"]),
	))
	conn.commit()
