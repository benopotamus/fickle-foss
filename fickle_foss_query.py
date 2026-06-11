#!/usr/bin/env python3
"""
fickle_foss_query.py - Query and report on the Fickle Foss database.

Usage:
	python3 fickle_foss_query.py		          	# Show app usage for last 30 days
	python3 fickle_foss_query.py --today          	# Show today's apps
	python3 fickle_foss_query.py --date 2024-03-15	# Show app usage for date
	python3 fickle_foss_query.py --week           	# Last 7 days summary
	python3 fickle_foss_query.py --month          	# Last 30 days summary
	python3 fickle_foss_query.py --alltime        	# Summary of all days
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "fickle_foss" / "fickle_foss.db"


def get_conn() -> sqlite3.Connection:
	if not DB_PATH.exists():
		print(f"Database not found at {DB_PATH}")
		print("The database is created by fickle_foss_tracker.py")
		raise SystemExit(1)
	return sqlite3.connect(DB_PATH)

def print_table(rows, headers):
	if not rows:
		print("  (no results)")
		return
	col_widths = [len(h) for h in headers]
	for row in rows:
		for i, cell in enumerate(row):
			col_widths[i] = max(col_widths[i], len(str(cell)))
	fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_widths)
	separator = "  " + "  ".join("-" * w for w in col_widths)
	print(fmt.format(*headers))
	print(separator)
	for row in rows:
		print(fmt.format(*[str(c) for c in row]))

def print_heading(s):
	'''Prints text with fancy formatting'''
	print('\n\033[1m# ' + s + '\033[0m\n')

###
# Queries
###

def show_day(conn: sqlite3.Connection, date: str):
	print_heading(f"Apps used on {date}")
	rows = conn.execute("""
		SELECT Apps.name
		FROM   DatesRun
		JOIN   Apps ON Apps.id = DatesRun.app_id
		WHERE  DatesRun.date = ?
		ORDER  BY Apps.name
	""", (date,)).fetchall()
	print_table(rows, ["App"])
	print()


def show_range(conn: sqlite3.Connection, start: str, end: str, label: str):
	print_heading(f"{label} ({start} → {end})")
	rows = conn.execute("""
		SELECT   Apps.name, COUNT(DISTINCT DatesRun.date) AS days_used
		FROM     DatesRun
		JOIN     Apps ON Apps.id = DatesRun.app_id
		WHERE    DatesRun.date BETWEEN ? AND ?
		GROUP BY Apps.name
		ORDER BY days_used DESC
	""", (start, end)).fetchall()
	print_table(rows, ["App", "Days Used"])
	print()


def show_all(conn: sqlite3.Connection):
	print_heading(f"All apps used (all recorded usage)")
	rows = conn.execute("""
		SELECT Apps.name, COUNT(DISTINCT DatesRun.date) AS days_used
		FROM   DatesRun
		JOIN   Apps ON Apps.id = DatesRun.app_id
		GROUP BY Apps.name
		ORDER  BY days_used DESC
	""").fetchall()
	print_table(rows, ["App", "Days Used"])
	print()


def show_default(conn: sqlite3.Connection, start: str, end: str):
	print_heading(f"Apps used last 30 days")
	rows = conn.execute("""
		SELECT   Apps.name, COUNT(DISTINCT DatesRun.date) AS days_used
		FROM     DatesRun
		JOIN     Apps ON Apps.id = DatesRun.app_id
		WHERE    DatesRun.date BETWEEN ? AND ?
		GROUP BY Apps.name
		ORDER BY days_used DESC
	""", (start, end)).fetchall()
	print_table(rows, ["App", "Days Used"])
	print()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
	parser = argparse.ArgumentParser(description="Query the Fickle FOSS database.")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("--today",   action="store_true",  help="show apps used today")
	group.add_argument("--date",    metavar="YYYY-MM-DD", help="show apps used on a specific date")
	group.add_argument("--week",    action="store_true",  help="show last 7 days")
	group.add_argument("--month",   action="store_true",  help="show last 30 days")
	group.add_argument("--all", action="store_true",  help="show all apps used (all time)")
	args = parser.parse_args()

	conn = get_conn()
	today = datetime.now().strftime("%Y-%m-%d")

	if args.today:
		show_day(conn, today)
	elif args.date:
		show_day(conn, args.date)
	elif args.week:
		start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
		show_range(conn, start, today, "Apps used last 7 days")
	elif args.month:
		start = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
		show_range(conn, start, today, "Apps used last 30 days")
	elif args.all:
		show_all(conn)
	else:
		# show_day(conn, today)
		start = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
		show_default(conn, start, today)

	conn.close()


if __name__ == "__main__":
	main()
