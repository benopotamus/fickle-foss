# state.py
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

from gi.repository import GObject, Gio

from . import db


class AppYearDonationState(GObject.Object):
	"""Holds the live 'amount donated this year' figure for one app (or the desktop
	environment, which is stored as an app - see db.get_or_create_app_id_for_de).

	amount_donated_this_year is a GObject.Property (not a plain attribute) so that
	anything bound to it - e.g. a label's "label" property via bind_property() - updates
	itself automatically whenever this changes, without the UI code needing to know that
	a donation happened.
	"""
	__gtype_name__ = 'AppYearDonationState'
	amount_donated_this_year = GObject.Property(type=int, default=0)


class AppStateStore(GObject.Object):
	"""Single source of truth for the donation figures that need to update live in the
	UI without a page refresh: 
		- Budget_remaining
		- one AppYearDonationState per app/DE (keyed by app_id),
		
	Created in main.py.
	Use `store = Gio.Application.get_default().store` to access
	"""
	__gtype_name__ = 'AppStateStore'
	budget_remaining = GObject.Property(type=int, default=0)

	def __init__(self):
		super().__init__()
		self._apps = {}  # app_id -> AppYearDonationState

		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.budget_remaining = self.settings.get_int("budget-remaining")

	def get_or_create(self, app_id, amount_donated_this_year=0.0):
		"""Returns the AppYearDonationState for app_id, creating it the first time it's
		asked for. 
		
		Callers that already know the current total (e.g. donate_page.py,
		which gets it as part of the query it already ran to build the row) can pass it
		in as the initial value to avoid a redundant DB query."""
		state = self._apps.get(app_id)
		if state is None:
			state = AppYearDonationState(amount_donated_this_year=amount_donated_this_year)
			self._apps[app_id] = state
		return state

	def record_donation_change(self, app_id):
		total = db.get_amount_donated_to_app_this_year(app_id)
		self.get_or_create(app_id).amount_donated_this_year = total

	def update_budget_remaining(self, amount):
		"""Updates the budget-remaining setting value by subtracting `amount`

		`amount` can be negative if a donation is being updated to have a lesser amount, or deleted!
		If `amount` is negative, the value is added back to budget-remaining."""
		self.budget_remaining = self.budget_remaining - amount
		self.settings.set_int("budget-remaining", self.budget_remaining)
