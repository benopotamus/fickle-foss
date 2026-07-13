#!/usr/bin/env python3

import argparse, sqlite3, locale
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "fickle-foss" / "fickle-foss.db"


def get_conn():
	if not DB_PATH.exists():
		# TODO add logging and make these error logs
		print(f"Database not found at {DB_PATH}")
		print("The database is created by fickle_foss_tracker.py")
		raise SystemExit(1)
	conn = sqlite3.connect(DB_PATH)
	#conn.row_factory = sqlite3.Row # Return dictionary instead of list of sets
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

def get_donations_groups(period):
	"""Returns a list of donations as sqlite3 Row's.
	Keys are:
		(donation) id
		(donation) date
		(donation) amount
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
			Apps.name,
			Apps.desktop_file
		FROM     Donations
		JOIN     Apps ON Apps.id = Donations.app_id
		ORDER BY Donations.date DESC
	""").fetchall()
	conn.close()

	# Group records by period
	def period_key(row):
		period_start_date = date.fromisoformat(row['date'])
		if period == "weekly":
			monday = period_start_date - timedelta(days=period_start_date.weekday())
			return f"Week of {monday.strftime(locale.nl_langinfo(locale.D_FMT))}"
		elif period == "monthly":
			return period_start_date.strftime("%B %Y")
		elif period == "yearly":
			return period_start_date.strftime("%Y")

	groups = {}
	for row in rows:
		key = period_key(row)
		groups.setdefault(key, []).append(row)
	return groups

def create_donation(donation_date, amount, app_id):
	"""Saves a donation"""
	conn = get_conn()
	conn.execute('''
		INSERT INTO Donations (date, amount, app_id)
		VALUES(?, ?, ?)
	''', (donation_date.strftime("%Y-%m-%d"), amount, app_id))
	conn.commit()
	conn.close()

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

def create_de_donation(donation_date, app_name, amount):
	"""Saves a donation to the current desktop environment (DE).

	The desktop environent isn't an app and doesn't have a guarenteed app
	record, so this function also checks if the DE is in the database as an app
	and adds if it if not."""
	conn = get_conn()

	# Check if the DE exists in the database already
	row = conn.execute('''SELECT id FROM Apps WHERE name=?''', (app_name,)).fetchone()
	de_id = row[0] if row else None # Get value from result tuple

	if de_id is None:
		de_id = conn.execute('''
			INSERT INTO Apps (name, desktop_file)
			VALUES(?, ?)
			RETURNING id
		''', (app_name, 'DE')).fetchone()[0]

	# Carry on adding the donation
	conn.execute('''
		INSERT INTO Donations (date, amount, app_id)
		VALUES(?, ?, ?)
	''', (donation_date.strftime("%Y-%m-%d"), amount, de_id))
	conn.commit()
	conn.close()

def get_amount_donated_to_de_this_year(de_name):
	conn = get_conn()
	total = conn.execute("""
		SELECT 	SUM(amount)
		FROM		Donations
		JOIN		Apps ON Apps.id = Donations.app_id
		WHERE	strftime('%Y', date)=? AND Apps.name=?
	""", (str(date.today().year), de_name)).fetchone()
	conn.close()
	return total[0]
	
