# preferences_dialog.py
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
from gi.repository import Adw
from gi.repository import Gtk, Gio

from .helpers import convert_amount_to_cents


@Gtk.Template(resource_path='/giving/fickle/foss/preferences-dialog.ui')
class PreferencesDialog(Adw.PreferencesDialog):
	__gtype_name__ = 'PreferencesDialog'

	freq_weekly = Gtk.Template.Child()
	freq_monthly = Gtk.Template.Child()
	freq_yearly = Gtk.Template.Child()
	# freq_infinite = Gtk.Template.Child()

	budget_amount = Gtk.Template.Child()
	currency_symbol = Gtk.Template.Child()
	# reminder_switchrow = Gtk.Template.Child()


	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.connect_frequency()
		self.connect_budget()

		# TODO add notifications if possible
		# self.settings.bind("reminder-notifications", self.reminder_switchrow, "active", Gio.SettingsBindFlags.DEFAULT)


	def connect_frequency(self):
		"""Connects/binds Frequency field with GSettings value.
		Uses signals instead of GSettings bind because the 4 GtkCheckboxes all change the same setting (and bind is 1-1 not M-1).
		"""
		frequency = self.settings.get_string("donation-frequency")
		# Select whichever one has the matching frequency value
		self.freq_weekly.set_active(frequency == "weekly")
		self.freq_monthly.set_active(frequency == "monthly")
		self.freq_yearly.set_active(frequency == "yearly")
		# self.freq_infinite.set_active(frequency == "infinite")

		self.freq_weekly.connect("toggled", self.on_frequency_toggled, "weekly")
		self.freq_monthly.connect("toggled", self.on_frequency_toggled, "monthly")
		self.freq_yearly.connect("toggled", self.on_frequency_toggled, "yearly")
		# self.freq_infinite.connect("toggled", self.on_frequency_toggled, "infinite")

	# SIGNAL
	def on_frequency_toggled(self, button, value):
		if button.get_active():
			self.settings.set_string("donation-frequency", value)


	def connect_budget(self):
		"""Connects/binds Budget field with GSettings value.
		Uses signals instead of GSettings bind because because it's a text field being stored as an integer and needs conversion
		"""
		money_int = self.settings.get_int("budget-amount")

		# Only show decimal places if needed
		# Use locale for decimal place so it uses the correct one for the locale
		if money_int % 100:
			self.budget_amount.set_text( locale.currency(money_int/100, symbol=False, grouping=True) )
		else:
			self.budget_amount.set_text(str(int(money_int/100)))

		self.currency_symbol.set_text(locale.localeconv()['currency_symbol'])
		self.budget_amount.connect("notify::text", self.on_budget_changed)

	# SIGNAL
	def on_budget_changed(self, budget_field, _):
		text = budget_field.get_text().strip()

		# Don't show error for empty field
		if not text:
			budget_field.remove_css_class("error")
			return

		money_cents = convert_amount_to_cents(text)

		if money_cents is None:
			# An amount of None from convert_amount_to_cents is an error state
			budget_field.add_css_class("error")
		else:
			self.settings.set_int("budget-amount", money_cents)
			budget_field.remove_css_class("error")

