# donate_dialog.py
#
# Copyright 2026 Ben Michie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import locale
from datetime import date, datetime

from gi.repository import Gtk, Gio, GObject, Adw

from . import db
from .helpers import convert_amount_to_cents

@Gtk.Template(resource_path='/giving/fickle/foss/donation-dialog.ui')
class DonationDialog(Adw.Dialog):
	__gtype_name__ = 'DonationDialog'
	app_icon = Gtk.Template.Child()
	app_name = Gtk.Template.Child()
	amount_field = Gtk.Template.Child()
	date_field = Gtk.Template.Child()
	save_button = Gtk.Template.Child()
	delete_button = Gtk.Template.Child()
	cancel_button = Gtk.Template.Child()

	def __init__(self, app_name, themed_icon, app_id=None, donation_id=None, donation_date=None, donation_amount=None, de=None, **kwargs):
		"""Set up the dialog

		This can be called in one of three ways:
			1. As a new donation (donation_id == False)
			2. As an update to an existing donation (donation_id != True)
			3. As a donation to the desktop environment (de == True)

		Each of these three ways have their own database function.
		"""
		super().__init__(**kwargs)

		self.app_icon.set_from_gicon(themed_icon)
		self.app_name.set_label(app_name)

		self.app_id = app_id
		self.donation_id = donation_id
		self.de = de

		# Hide delete button if no donation_id (which indicates this is a new donation, not an edit to an existing one)
		if not donation_id:
			self.delete_button.set_visible(False)

		if donation_amount:
			self.amount_field.set_text(donation_amount)

		# Set default value of date field using locale formatting
		# https://docs.python.org/3/library/locale.html#locale.nl_langinfo
		if donation_date:
			date_ = date.fromisoformat(donation_date)
		else:
			# Default to today's date for new donations
			date_ = date.today()

		self.date_field.set_text(date_.strftime(locale.nl_langinfo(locale.D_FMT)))

		self.amount_field.connect("notify::text", self.on_amount_changed)
		self.date_field.connect("notify::text", self.on_date_changed)
		self.save_button.connect("clicked", self.on_save_clicked)
		self.delete_button.connect("clicked", self.on_delete_clicked)
		self.cancel_button.connect("clicked", self.on_cancel_clicked)


	# SIGNAL
	def on_amount_changed(self, amount_field, _):
		"""Validates amount field as user types - adding/removing error class as needed."""
		amount_field.remove_css_class("error")

		text = amount_field.get_text().strip()

		# No error for empty field
		if not text:
			return

		# convert_amount_to_cents also does validation
		money_cents = convert_amount_to_cents(text)

		if money_cents is None:
			# An amount of None from convert_amount_to_cents is an error (it couldn't do the conversion)
			amount_field.add_css_class("error")
		else:
			amount_field.remove_css_class("error")

	# SIGNAL
	def on_date_changed(self, date_field, _):
		"""Validate date field as user types.
		Ideally date field would be a datepicker and the user cannot enter dates manually."""
		self.validate_date(date_field)

	# SIGNAL
	def on_save_clicked(self, _):
		"""Validates fields then saves the donation details to the database."""
		donation_date = self.validate_date(self.date_field)

		# If user clicks Save with no data in these mandatory fields, they should see an error instead
		if not self.amount_field.get_text():
			self.amount_field.add_css_class("error")
		if not self.date_field.get_text():
			self.date_field.add_css_class("error")

		# Only save if both fields are valid (not empty)
		if self.amount_field.get_text() and self.date_field.get_text():
			if self.donation_id:
				db.update_donation(donation_date, self.amount_field.get_text(), self.donation_id)
			elif self.app_id:
				db.create_donation(donation_date, self.amount_field.get_text(), self.app_id)
			elif self.de:
				db.create_de_donation(donation_date, self.app_name.get_text(), self.amount_field.get_text())

			self.get_root().emit('donation-updated')
			self.close()

	# SIGNAL
	def on_delete_clicked(self, _):
		"""Deletes the donation from the database."""
		db.delete_donation(self.donation_id)
		self.get_root().emit('donation-deleted')
		self.close()

	# SIGNAL
	def on_cancel_clicked(self, _):
		self.close()

	def validate_date(self, date_field):
		"""Validates date field - adding/removing error class as needed."""
		date_field.remove_css_class("error")

		text = date_field.get_text().strip()

		# No error for empty field
		if not text:
			return

		# Get the locale specific format of the field
		# https://docs.python.org/3/library/locale.html#locale.nl_langinfo
		date_str_format = locale.nl_langinfo(locale.D_FMT)

		try:
			date_ = datetime.strptime(text, date_str_format).date()
			date_field.remove_css_class("error")
			return date_
		# ValueError is raised if date string doesn't match locale format
		except ValueError:
			date_field.add_css_class("error")
			return None

