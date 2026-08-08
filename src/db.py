#!/usr/bin/env python3

import sqlite3
from datetime import date
from pathlib import Path

from . import helpers

DB_PATH = Path.home() / ".local" / "share" / "fickle-foss" / "fickle-foss.db"


def get_conn():
	if not DB_PATH.exists():
		# TODO add logging and make these error logs
		print(f"Database not found at {DB_PATH}")
		print("The database is created by fickle_foss_tracker.py")
		raise SystemExit(1)
	conn = sqlite3.connect(DB_PATH)
	return conn


def get_apps_used_list(date_from, date_to):
	"""Returns a list of applications as sqlite3 Row's.
	Keys are:
		id
		name
		desktop_file
		days_used
	"""
	conn = get_conn()
	conn.row_factory = sqlite3.Row
	apps_used = conn.execute("""
		SELECT
				Apps.id, Apps.name, Apps.desktop_file,
				COUNT(DISTINCT DatesRun.date) AS days_used,
				COALESCE(YearDonations.total, 0) AS amount_donated_this_year
		FROM		DatesRun
		JOIN		Apps ON Apps.id = DatesRun.app_id

		LEFT JOIN (
			SELECT app_id, SUM(amount) AS total
			FROM   Donations
			WHERE  strftime('%Y', date) = ?
			GROUP BY app_id
		) AS YearDonations ON YearDonations.app_id = Apps.id

		WHERE	DatesRun.date BETWEEN ? AND ?
		GROUP BY Apps.id
		ORDER BY days_used DESC
	""", (str(date.today().year), date_from, date_to)).fetchall()
	conn.close()
	return apps_used

def get_donations_groups(donation_freq):
	"""Returns a list of donations as sqlite3 Row's.
	Keys are:
		(donation) id
		(donation) date
		(donation) amount
		(donation) app_id
		(app) name
		(app) desktop_file
	"""
	conn = get_conn()
	conn.row_factory = sqlite3.Row
	rows = conn.execute("""
		SELECT
			Donations.id,
			Donations.date,
			Donations.amount,
			Donations.app_id,
			Apps.name,
			Apps.desktop_file
		FROM     Donations
		JOIN     Apps ON Apps.id = Donations.app_id
		ORDER BY Donations.date DESC
	""").fetchall()
	conn.close()

	# Group records by period
	groups = {}
	for row in rows:
		key = helpers.get_period_name(date.fromisoformat(row['date']), donation_freq)
		groups.setdefault(key, []).append(row)
	return groups

def create_donation(donation_date, amount, app_id):
	"""Saves a donation"""
	conn = get_conn()
	donation_id = conn.execute('''
		INSERT INTO Donations (date, amount, app_id)
		VALUES(?, ?, ?)
		RETURNING id
	''', (donation_date.strftime("%Y-%m-%d"), amount, app_id)).fetchone()[0]
	conn.commit()
	conn.close()
	return donation_id

def update_donation(donation_date, amount, donation_id):
	"""Saves a donation"""
	conn = get_conn()
	conn.execute('''
		UPDATE Donations
		SET
			date=?,
			amount=?
		WHERE id=?
	''', (donation_date.strftime("%Y-%m-%d"), amount, donation_id))
	conn.commit()
	conn.close()

def delete_donation(donation_id):
	"""Deletes a donation"""
	conn = get_conn()
	conn.execute('''	DELETE FROM Donations WHERE id=?''', (donation_id,))
	conn.commit()
	conn.close()

def get_or_create_app_id_for_de(de_name):
	"""Returns the Apps.id and amount_donated_this_year for the current desktop environment.
	Note: The DE is stored as an ordinary row in Apps (with desktop_file='DE').
	"""
	conn = get_conn()
	conn.row_factory = sqlite3.Row
	row = conn.execute("""
		SELECT 	id, 
				COALESCE(YearDonations.total, 0) AS amount_donated_this_year
		FROM 	Apps 
				LEFT JOIN (
					SELECT app_id, SUM(amount) AS total
					FROM   Donations
					WHERE  strftime('%Y', date) = ?
					GROUP BY app_id
				) AS YearDonations ON YearDonations.app_id = Apps.id
		WHERE 	name=?
		""", (str(date.today().year), de_name)).fetchone()
	if row:
		de_id = row[0]
		amount_donated_this_year = row[1]
	else:
		de_id = conn.execute('''
			INSERT INTO Apps (name, desktop_file)
			VALUES(?, ?)
			RETURNING id
		''', (de_name, 'DE')).fetchone()[0]
		amount_donated_this_year = 0
	conn.commit()
	return de_id, amount_donated_this_year

def get_amount_donated_to_app_this_year(app_id):
	"""Returns the total amount donated to a given app (or the DE "app") so far this year. 
	Returns 0 if there are no donations yet."""
	conn = get_conn()
	total = conn.execute("""
		SELECT 	SUM(amount)
		FROM	Donations
		WHERE	strftime('%Y', date)=? AND app_id=?
	""", (str(date.today().year), app_id)).fetchone()
	conn.close()
	return total[0] or 0
