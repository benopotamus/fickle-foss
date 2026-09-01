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

from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
from gi.repository import Adw, Gtk, Gio, GObject

from . import db
from . import helpers
from .donation_dialog import DonationDialog


# Get list of apps that should not be displayed in the app list. E.g. 'steam.desktop'
try:
	with open(Path.home() / ".local" / "share" / "fickle-foss" / "ignore-list", 'r') as file:
		IGNORE = file.read().splitlines()
except FileNotFoundError:
	IGNORE = []


@Gtk.Template(resource_path='/giving/fickle/foss/donate-page.ui')
class DonatePage(Gtk.Box):
	__gtype_name__ = 'DonatePage'
	de_box = Gtk.Template.Child()
	apps_listbox = Gtk.Template.Child()
	apps_list_stack = Gtk.Template.Child()
	apps_placeholder = Gtk.Template.Child()
	last_x_days_heading = Gtk.Template.Child()


	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.store = Gio.Application.get_default().store

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
		de_name = helpers.get_de_name()
		de_app_id, de_amount_donated_this_year = db.get_or_create_app_id_for_de(de_name)
		de_row = Adw.ActionRow(title=de_name)
		de_row.app_id = de_app_id
		de_row.desktop_file = 'DE'

		self.populate_row(
			de_row, 
			helpers.get_app_icon_image('DE', 64), # this will lookup the correct icon for the DE where possible
			de_amount_donated_this_year
		)

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
		self.to_date = self.date_

		if self.donation_freq == "weekly":
			self.from_date = self.date_ - timedelta(days=7)

		elif self.donation_freq == "monthly":
			self.from_date = self.date_ - timedelta(days=30)

		elif self.donation_freq == "yearly":
			self.from_date = self.date_ - timedelta(days=365)

		# TODO maybe add infinite in the future. All donations are lumped in the same period.
		# elif self.donation_freq == "infinite":
		# 	self.from_date = date_.min


	def set_period_name(self):
		"""Sets the '[x] days' labels
		"""
		if self.donation_freq == "weekly":
			days = 7
		elif self.donation_freq == "monthly":
			days = 30
		elif self.donation_freq == "yearly":
			days = 365
		
		self.last_x_days_heading.set_label(f"Usage over last {days} days")
		self.apps_placeholder.set_description(f"No apps used in the last {days} days")


	def populate_apps_used_list(self):
		# Clear list before populating (not needed first time, but needed all other times)
		self.apps_listbox.remove_all()
		apps_used_list = db.get_apps_used_list(self.from_date.strftime("%Y-%m-%d"), self.to_date.strftime("%Y-%m-%d"))

		for app in apps_used_list:
			row = Adw.ActionRow(title=app['name'])

			# Add app id to row so it can be used later when saving donations
			row.app_id = app['id']
			row.desktop_file = app['desktop_file']

			# Skip apps that are in the ignore list
			# Predominantly for ignoring apps that don't want donations e.g. 'steam.desktop'
			if app['desktop_file'] in IGNORE:
				continue

			self.populate_row(
				row, 
				helpers.get_app_icon_image(app['desktop_file'], 64),
				app['amount_donated_this_year'],
				app['days_used'],
			)
			self.apps_listbox.append(row)

		# Display the listbox or placeholder StackPage based on whether there are any apps to display
		if apps_used_list:
			self.apps_list_stack.set_visible_child(self.apps_listbox)
		else:
			self.apps_list_stack.set_visible_child(self.apps_placeholder)

	def populate_row(self, row, icon_image, amount_donated_this_year=0, days_used=None):
		icon_image.add_css_class('icon-dropshadow')
		icon_image.set_margin_top(12)
		icon_image.set_margin_bottom(12)
		row.add_prefix(icon_image)
		if days_used:
			row.set_subtitle(f"{str(days_used)} days")

		box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
		label_amount = Gtk.Label()
		label_amount.add_css_class('caption')
		label_amount.add_css_class('bold')
		label_clarifier = Gtk.Label(label='(this year)')
		label_clarifier.add_css_class('subtitle')
		box.append(label_amount)
		box.append(label_clarifier)
		row.add_suffix(box)

		# Bind to Store so values are updated without refreshing whole list (and losing scroll position)
		state = self.store.get_or_create(row.app_id, amount_donated_this_year=amount_donated_this_year)
		self.bind_amount_donated(state, label_amount, box)

		row.set_activatable(True)

	# SIGNAL
	def on_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		dialog = DonationDialog(
			app_id = row.app_id,
			app_name = row.get_title(),
			desktop_file = row.desktop_file,
		)
		dialog.present(self)
