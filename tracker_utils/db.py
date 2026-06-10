import os
import sqlite3
import datetime


def init_db(db_path):
	'''Set up database - create tables etc'''
	os.makedirs(os.path.dirname(db_path), exist_ok=True)
	conn = sqlite3.connect(db_path)

	# Enable foreign key enforcement (off by default in SQLite)
	conn.execute('PRAGMA foreign_keys = ON')

	conn.execute('''
		CREATE TABLE IF NOT EXISTS Apps (
			id				INTEGER PRIMARY KEY AUTOINCREMENT,
			name			TEXT	NOT NULL,
			desktop_file	TEXT	NOT NULL UNIQUE
		)
	''')

	conn.execute('''
		CREATE TABLE IF NOT EXISTS DatesRun (
			id		INTEGER PRIMARY KEY AUTOINCREMENT,
			date	TEXT	NOT NULL,
			app_id	INTEGER NOT NULL,
			FOREIGN KEY (app_id) REFERENCES Apps(id),
			UNIQUE (date, app_id)
		)
	''')

	conn.execute('''
		CREATE TABLE IF NOT EXISTS Donations (
			id		INTEGER PRIMARY KEY AUTOINCREMENT,
			date	TEXT	NOT NULL,
			amount	INTEGER	NOT NULL,
			app_id	INTEGER NOT NULL,
			FOREIGN KEY (app_id) REFERENCES Apps(id)
		)
	''')

	conn.commit()
	return conn

def log_app(conn, app):
	'''Records that an app was run today (ignores if already recorded).
	Also creates an Apps record if one doesn't exist already.
	'''
	date = datetime.date.today().strftime("%Y-%m-%d")
	conn.execute('PRAGMA foreign_keys = ON')

	conn.execute('''
		INSERT OR IGNORE INTO Apps (name, desktop_file)
		VALUES (?, ?)
	''', (app['app_name'], app['desktop_file_name']))

	conn.execute('''
		INSERT OR IGNORE INTO DatesRun (date, app_id)
		SELECT ?, id FROM Apps WHERE name = ?
	''', (date, app['app_name']))

	conn.commit()
