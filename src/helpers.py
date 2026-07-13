import locale, math, os
from datetime import date
from gi.repository import Gtk, Gio

def convert_amount_to_cents(text: str) -> int | None:
	"""
	Parse a user-entered amount string to integer cents.
	Returns None if the input is invalid.
	"""
	text = text.strip()
	if not text:
		return None

	try:
		# locale.atof() respects the current locale's decimal separator
		# so "1,55" works for European locales and "1.55" for others
		amount = locale.atof(text)
	except ValueError:
		return None

	if amount < 0:
		return None

	# Round to avoid floating point errors (e.g. 1.1 * 100 = 110.00000000000001)
	return math.floor(round(amount * 100))

def get_amount_as_locale_str(amount, symbol=False):
	"""Returns the amount value as a locale formatted string - with optional currency symbol."""
	# TODO handle locales where the currency symbol is at the end. Maybe use Babel?
	decimal_char = locale.localeconv()["mon_decimal_point"]
	return locale.currency(amount, grouping=True, symbol=symbol).rstrip('0').rstrip(decimal_char) # The rstrips here aim to return whole numbers where possible

def get_de_name_and_icon():
	"""Returns the desktop environment name and icon"""
	# TODO add icons for other desktop environments
	name = os.environ.get("XDG_CURRENT_DESKTOP", "") or None

	if name == "GNOME":
		icon = Gio.ThemedIcon.new("start-here")
	else:
		icon = Gio.ThemedIcon.new("item-missing-symbolic")

	return name, icon
	
