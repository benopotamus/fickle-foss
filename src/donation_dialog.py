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
from decimal import Decimal

from gi.repository import Gtk, Gio, Adw

from . import db
from . import helpers


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

	def __init__(self, app_name, themed_icon, app_id, donation_id=None, donation_date=None, donation_amount=None, **kwargs):
		"""Set up the dialog

		This can be called in one of two ways:
			1. As a new donation (donation_id is None)
			2. As an update to an existing donation (donation_id is set)
		"""
		super().__init__(**kwargs)

		self.store = Gio.Application.get_default().store

		self.app_icon.set_from_gicon(themed_icon)
		self.app_name.set_label(app_name)

		self.app_id = app_id
		self.donation_id = donation_id
		self.app_name_text = app_name
		self.themed_icon = themed_icon

		# Hide delete button if no donation_id (which indicates this is a new donation, not an edit to an existing one)
		if not donation_id:
			self.delete_button.set_visible(False)

		self.original_amount = 0
		if donation_amount:
			self.amount_field.set_text(str(helpers.to_money(donation_amount, symbol=False)))
			self.original_amount = donation_amount # We keep the original donation amount so the new amount can be compared to the original amount to work out what the budget-remaining value should be.

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
		"""Validates amount field on keypress - adding/removing error class as needed."""
		amount_field.remove_css_class("error")

		text = amount_field.get_text().strip()

		# No error for empty field
		if not text:
			return

		money_cents = helpers.to_int(text) # returns None if not a valid number

		if money_cents is None:
			amount_field.add_css_class("error")
		else:
			amount_field.remove_css_class("error")

	# SIGNAL
	def on_date_changed(self, date_field, _):
		"""Validate date field on keypress.
		TODO Ideally date field would be a datepicker and the user would not enter dates manually."""
		self.validate_date(date_field)

	# SIGNAL
	def on_save_clicked(self, _):
		"""Validates fields then saves the donation details to the database.
		amount_field is not actually validated here because it is validated whenever the value of it changes, see on_amount_changed"""
		donation_date = self.validate_date(self.date_field)

		# If user clicks Save with no data in these mandatory fields, they should see an error instead
		if not self.amount_field.get_text():
			self.amount_field.add_css_class("error")
		if not self.date_field.get_text():
			self.date_field.add_css_class("error")

		if self.amount_field.get_text() and self.date_field.get_text():
			amount_cents = helpers.to_int(Decimal(self.amount_field.get_text()))
			if amount_cents is None or donation_date is None:
				return

			if self.donation_id:
				db.update_donation(donation_date, amount_cents, self.donation_id)
				self.get_root().donations_page.handle_donation_updated(
					self.donation_id, donation_date.isoformat(), amount_cents
				)
			else:
				donation_id = db.create_donation(donation_date, amount_cents, self.app_id)
				self.get_root().donations_page.handle_donation_created(
					donation_id, self.app_id, self.app_name_text, self.themed_icon,
					donation_date.isoformat(), amount_cents
				)

			self.store.record_donation_change(self.app_id)
			self.store.update_budget_remaining(amount_cents - self.original_amount)
			self.close()

	# SIGNAL
	def on_delete_clicked(self, _):
		"""Deletes the donation from the database."""
		db.delete_donation(self.donation_id)
		self.get_root().donations_page.handle_donation_deleted(self.donation_id)
		self.store.record_donation_change(self.app_id)
		self.store.update_budget_remaining(-self.original_amount)
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
