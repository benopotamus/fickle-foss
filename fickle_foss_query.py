#!/usr/bin/env python3
"""
fickle_foss_query.py - Query and report on the Fickle Foss database.

Usage:
	python3 fickle_foss_query.py                  # Show today's apps
	python3 fickle_foss_query.py --date 2024-03-15
	python3 fickle_foss_query.py --week           # Last 7 days summary
	python3 fickle_foss_query.py --month          # Last 30 days summary
	python3 fickle_foss_query.py --all            # All recorded days
	python3 fickle_foss_query.py --stats          # Most-used apps overall
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "fickle_foss" / "fickle_foss.db"

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
	if not DB_PATH.exists():
		print(f"Database not found at {DB_PATH}")
		print("Make sure fickle_foss_tracker.py has been running first.")
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


# ── Query functions ────────────────────────────────────────────────────────────

def show_day(conn: sqlite3.Connection, date: str):
	print(f"\n── Apps launched on {date} ──\n")
	rows = conn.execute("""
		SELECT app_name
		FROM   app_launches
		WHERE  date = ?
		ORDER  BY app_name
	""", (date,)).fetchall()
	print_table(rows, ["Application"])
	print(f"\n  {len(rows)} app(s) recorded.\n")


def show_range(conn: sqlite3.Connection, start: str, end: str, label: str):
	print(f"\n── {label} ({start} → {end}) ──\n")
	rows = conn.execute("""
		SELECT date, app_name
		FROM   app_launches
		WHERE  date BETWEEN ? AND ?
		ORDER  BY date DESC, app_name
	""", (start, end)).fetchall()
	print_table(rows, ["Date", "Application"])
	print(f"\n  {len(rows)} launch(es) across {len({r[0] for r in rows})} day(s).\n")


def show_all(conn: sqlite3.Connection):
	print("\n── All recorded launches ──\n")
	rows = conn.execute("""
		SELECT date, app_name
		FROM   app_launches
		ORDER  BY date DESC, app_name
	""").fetchall()
	print_table(rows, ["Date", "Application"])
	print(f"\n  {len(rows)} launch(es) across {len({r[0] for r in rows})} day(s).\n")


def show_stats(conn: sqlite3.Connection):
	print("\n── Most-used applications (all time) ──\n")
	rows = conn.execute("""
		SELECT   app_name,
				 COUNT(DISTINCT date) AS days_used,
				 MIN(date)            AS first_seen,
				 MAX(date)            AS last_seen
		FROM     app_launches
		GROUP BY app_name
		ORDER BY days_used DESC
	""").fetchall()
	print_table(rows, ["Application", "Days Used", "First Seen", "Last Seen"])
	print()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
	parser = argparse.ArgumentParser(description="Query the Fickle Foss database.")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("--date",  metavar="YYYY-MM-DD", help="Show launches for a specific date")
	group.add_argument("--week",  action="store_true",  help="Show last 7 days")
	group.add_argument("--month", action="store_true",  help="Show last 30 days")
	group.add_argument("--all",   action="store_true",  help="Show all recorded data")
	group.add_argument("--stats", action="store_true",  help="Show per-app usage statistics")
	args = parser.parse_args()

	conn = get_conn()
	today = datetime.now().strftime("%Y-%m-%d")

	if args.date:
		show_day(conn, args.date)
	elif args.week:
		start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
		show_range(conn, start, today, "Last 7 days")
	elif args.month:
		start = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
		show_range(conn, start, today, "Last 30 days")
	elif args.all:
		show_all(conn)
	elif args.stats:
		show_stats(conn)
	else:
		show_day(conn, today)

	conn.close()


if __name__ == "__main__":
	main()
