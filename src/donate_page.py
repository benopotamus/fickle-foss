# donate_page.py
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

from datetime import date, timedelta
from calendar import monthrange
from decimal import Decimal
from gi.repository import Adw, Gtk, Gio, GObject

from . import db
from . import helpers
from .donation_dialog import DonationDialog

@Gtk.Template(resource_path='/giving/fickle/foss/donate-page.ui')
class DonatePage(Gtk.Box):
	__gtype_name__ = 'DonatePage'
	de_box = Gtk.Template.Child()
	apps_listbox = Gtk.Template.Child()
	apps_list_stack = Gtk.Template.Child()
	apps_placeholder = Gtk.Template.Child()
	period_name = Gtk.Template.Child()
	prev_period_button = Gtk.Template.Child()
	next_period_button = Gtk.Template.Child()


	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.store = Gio.Application.get_default().store

		self.prev_period_button.connect("clicked", self.show_prev_period)
		self.next_period_button.connect("clicked", self.show_next_period)

		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.donation_freq = self.settings.get_string("donation-frequency") # e.g. "monthly"

		# Listen for changes to the frequency setting
		self.settings.connect("changed::donation-frequency", self.on_frequency_changed)

		# Populate list on app startup
		self.init_period()
		self.set_period_name()
		self.populate_apps_used_list()

		# The user's desktop environment has a permanent place on the donate page
		# e.g. "GNOME", "KDE", "XFCE"
		de_name, de_icon = helpers.get_de_name_and_icon()
		de_app_id, de_amount_donated_this_year = db.get_or_create_app_id_for_de(de_name)
		de_row = Adw.ActionRow(title=de_name)
		de_row.app_id = de_app_id
		de_row.themed_icon = de_icon # Store themed icon so it can be passed to dialog box later
		self.populate_row(de_row, de_amount_donated_this_year)
		de_row.set_activatable(True)
		self.de_box.append(de_row)
		self.de_box.connect("row-activated", self.on_row_clicked)

		# Open donation dialog box when an app row (or the DE row) is clicked
		self.apps_listbox.connect("row-activated", self.on_row_clicked)

	def bind_amount_donated(self, state, label, box):
		"""Binds an AppYearDonationState's amount_donated_this_year to a label's text
		(formatted as money) and to a box's visibility (hidden when there's nothing
		donated yet).
		"""
		state.bind_property(
			"amount-donated-this-year", label, "label",
			GObject.BindingFlags.SYNC_CREATE,
			transform_to=lambda _binding, amount: helpers.to_money(Decimal(amount)) if amount else ""
		)
		state.bind_property(
			"amount-donated-this-year", box, "visible",
			GObject.BindingFlags.SYNC_CREATE,
			transform_to=lambda _binding, amount: bool(amount)
		)

	def on_frequency_changed(self, settings, key):
		self.donation_freq = settings.get_string(key)
		self.init_period()
		self.set_period_name()
		self.populate_apps_used_list()

	def init_period(self):
		# from_date is always today so the user always starts with today's period
		self.date_ = date.today()

		if self.donation_freq == "weekly":
			# A "week" is Monday to Sunday
			# We set `from_date` to the 1st day of the current week by subtracting whatever `weekday()` (Monday==0)
			# And set `to_date` to 6 days later (which 1st+6=7)
			self.from_date = self.date_ - timedelta(days=self.date_.weekday())
			self.to_date = self.from_date + timedelta(days=6)

		elif self.donation_freq == "monthly":
			self.from_date = self.date_.replace(day=1)
			# to_date is dependent on how many days in the month - uses calendar.monthrange
			# https://docs.python.org/3/library/calendar.html#calendar.monthrange
			self.to_date = self.from_date.replace(day=monthrange(self.from_date.year, self.from_date.month)[1])

		elif self.donation_freq == "yearly":
			self.from_date = self.date_.replace(day=1, month=1)
			# to_date is 31 December of current year
			self.to_date = self.from_date.replace(day=31, month=12)

		# TODO maybe add infinite in the future. All donations are lumped in the same period.
		# elif self.donation_freq == "infinite":
		# 	self.from_date = date_.min
		# 	self.to_date = date_.max


	def set_period_name(self):
		"""Sets the period_name label
		`self.from_date` is added to self by `self.init_period` - which is always called first.
		"""
		self.period_name.set_label(helpers.get_period_name(self.from_date, self.donation_freq))


	def populate_apps_used_list(self):
		# Clear list before populating (not needed first time, but needed all other times)
		self.apps_listbox.remove_all()
		apps_used_list = db.get_apps_used_list(self.from_date.strftime("%Y-%m-%d"), self.to_date.strftime("%Y-%m-%d"))

		for app in apps_used_list:
			row = Adw.ActionRow(title=app['name'])

			# Add app id to row so it can be used later when saving donations
			row.app_id = app['id']

			# Get icon from desktop file
			desktop_file_name = app['desktop_file'] # e.g. 'geany.desktop'

			try:
				app_info = Gio.DesktopAppInfo.new(desktop_file_name)
				# Store themed_icon on row so it can be passed to DonationDialog
				row.themed_icon = app_info.get_icon() # Returns a Gio.ThemedIcon
				if row.themed_icon is None:
					continue
			# Uninstalled apps remove their desktop file which causes this TypeError when trying to get the app's icon
			# This fallback uses the default "app with no icon" icon
			except TypeError:
				row.themed_icon = Gio.ThemedIcon.new('application-x-executable')

			self.populate_row(row, app['amount_donated_this_year'], app['days_used'])
			self.apps_listbox.append(row)

		# Display the listbox or placeholder StackPage based on whether there are any apps to display
		if apps_used_list:
			self.apps_list_stack.set_visible_child(self.apps_listbox)
		else:
			self.apps_list_stack.set_visible_child(self.apps_placeholder)

	def populate_row(self, row, amount_donated_this_year=0, days_used=None):
		icon = Gtk.Image.new_from_gicon(row.themed_icon)
		# icon.set_icon_size(Gtk.IconSize.LARGE)
		icon.add_css_class('icon-dropshadow')
		icon.set_pixel_size(64)
		icon.set_margin_top(12)
		icon.set_margin_bottom(12)
		row.add_prefix(icon)
		if days_used:
			row.set_subtitle(f"{str(days_used)} days")

		# Tag showing the amount donated this year - bound to the store (seeded with
		# the value this query just fetched) so it updates live on donation changes,
		# without needing populate_apps_used_list to run again.
		box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
		label_amount = Gtk.Label()
		label_amount.add_css_class('caption')
		label_amount.add_css_class('bold')
		label_clarifier = Gtk.Label(label='(this year)')
		label_clarifier.add_css_class('subtitle')
		box.append(label_amount)
		box.append(label_clarifier)
		row.add_suffix(box)

		state = self.store.get_or_create(row.app_id, amount_donated_this_year=amount_donated_this_year)
		self.bind_amount_donated(state, label_amount, box)

		row.set_activatable(True)

	# SIGNAL
	def show_next_period(self, _):
		"""Sets the instance's variables of from_date and to_date to the next period's values, and updates the apps list with records within that range."""
		if self.donation_freq == "weekly":
			self.from_date = self.from_date + timedelta(weeks=1)
			self.to_date = self.to_date + timedelta(weeks=1)

		elif self.donation_freq == "monthly":
			self.from_date = self.to_date + timedelta(days=1) # +1 day to get to the next month
			# to_date is dependent on how many days in the month - uses calendar.monthrange to get the number of days in from_date's month
			# https://docs.python.org/3/library/calendar.html#calendar.monthrange
			self.to_date = self.from_date.replace(day=monthrange(self.from_date.year, self.from_date.month)[1])

		elif self.donation_freq == "yearly":
			self.from_date = self.to_date + timedelta(days=1) # +1 day to get to the next year
			self.to_date = self.from_date.replace(day=31, month=12) # 31 December of from_date's year

		self.populate_apps_used_list()
		self.set_period_name()

	# SIGNAL
	def show_prev_period(self, _):
		"""Sets the instance's variables of from_date and to_date to the previous period's values, and updates the apps list with records within that range."""
		if self.donation_freq == "weekly":
			self.from_date = self.from_date - timedelta(weeks=1)
			self.to_date = self.to_date - timedelta(weeks=1)

		elif self.donation_freq == "monthly":
			self.to_date = self.from_date - timedelta(days=1) # -1 day to get to the last day of the previous month month
			self.from_date = self.to_date.replace(day=1)

		elif self.donation_freq == "yearly":
			self.to_date = self.from_date - timedelta(days=1) # -1 day to get to the last day of the previous year
			self.from_date = self.to_date.replace(day=1, month=1) # 31 December of to_date's year

		self.populate_apps_used_list()
		self.set_period_name()

	# SIGNAL
	def on_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		dialog = DonationDialog(
			app_id = row.app_id,
			app_name = row.get_title(),
			themed_icon = row.themed_icon,
		)
		dialog.present(self)
