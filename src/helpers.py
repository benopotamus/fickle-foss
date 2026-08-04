import locale, os
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from gi.repository import Gtk, Gio


def get_period_name(date_, donation_freq):
	"""Returns the name of the period that date_ is in, based on the donation frequency setting.
	E.g. with a donation frequency of "monthly", a period name might be 'July 2026'. 

	NOTE: This is used for UI labels AND dictionary keys.

	UI labels
		Donations Page: group names (via db.get_donations_groups)
		Donate Page: period name next to the period selection back/forward buttons

	Keys
		Donations Page: Each donation group has a name and is used when a donation is updated to check if it has moved to a different period.
	"""
	if donation_freq == "weekly":
		monday = date_ - timedelta(days=date_.weekday())
		return f"Week of {monday.strftime(locale.nl_langinfo(locale.D_FMT))}"
	elif donation_freq == "monthly":
		return date_.strftime("%B %Y")
	elif donation_freq == "yearly":
		return date_.strftime("%Y")


def get_period_range(donation_frequency, date_=None):
	"""Returns the period bounds (start and end dates) for the provided date and donation_frequency value.

	`donation_frequency` is the gsettings donation_frequency value (weekly, monthly, yearly)
	Defaults to current date if no date provided.
	"""
	if date_ == None:
		date_ = date.today()

	if donation_frequency == "weekly":
		# A "week" is Monday to Sunday
		# We set `from_date` to the 1st day of the current week by subtracting whatever `weekday()` is (Monday==0)
		# And set `to_date` to 6 days later (which 1st+6=7)
		from_date = date_ - timedelta(days=date_.weekday())
		to_date = from_date + timedelta(days=6)

	elif donation_frequency == "monthly":
		from_date = date_.replace(day=1)
		# to_date is dependent on how many days in the month - uses calendar.monthrange
		# https://docs.python.org/3/library/calendar.html#calendar.monthrange
		to_date = from_date.replace(day=monthrange(from_date.year, from_date.month)[1])

	elif donation_frequency == "yearly":
		from_date = date_.replace(day=1, month=1)
		# to_date is 31 December of current year
		to_date = from_date.replace(day=31, month=12)

	# TODO maybe add infinite in the future. All donations are lumped in the same period.
	# elif donation_frequency == "infinite":
	# 	from_date = date_.min
	# 	to_date = date_.max

	return from_date, to_date

def to_int(amount):
	"""Converts a decimal value (Decimal or String) to an int representing cents (value*100)"""
	if isinstance(amount, str):
		try:
			amount = Decimal(amount.strip())
		except ValueError:
			return None
	return int(amount * 100)

def to_money(amount, symbol=True):
	"""Returns amount as a locale formatted money string - with monetary symbol.
	Set `symbol` to False not include monetary symbol.
	"""
	# TODO handle locales where the currency symbol is at the end. Maybe use Babel?
	decimal_char = locale.localeconv()["mon_decimal_point"]
	return locale.currency(amount/100, grouping=True, symbol=symbol).rstrip('0').rstrip(decimal_char) # The rstrips here aim to return whole numbers where possible

def get_de_name_and_icon():
	"""Returns the desktop environment name and icon"""
	# TODO add icons for other desktop environments
	name = os.environ.get("XDG_CURRENT_DESKTOP", "") or None

	if name == "GNOME":
		icon = Gio.ThemedIcon.new("start-here")
	else:
		icon = Gio.ThemedIcon.new("item-missing-symbolic")

	return name, icon
