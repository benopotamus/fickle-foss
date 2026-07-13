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

import locale
from datetime import date, timedelta
from calendar import monthrange
from gi.repository import Adw, Gtk, Gio

from .db import get_apps_used_list, get_amount_donated_to_de_this_year
from .helpers import get_de_name_and_icon, get_amount_as_locale_str
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
		self.prev_period_button.connect("clicked", self.show_prev_period)
		self.next_period_button.connect("clicked", self.show_next_period)

		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.period = self.settings.get_string("donation-frequency") # e.g. "monthly"

		# Listen for changes to the frequency setting
		self.settings.connect("changed::donation-frequency", self.on_frequency_changed)

		# Populate list on app startup
		self.init_period()
		self.set_period_name()
		self.populate_apps_used_list()


		# The user's desktop environment has a permanent place on the donate page
		# e.g. "GNOME", "KDE", "XFCE"
		de_name, de_icon = get_de_name_and_icon()
		de_row = Adw.ActionRow(title=de_name)
		de_row.themed_icon = de_icon # Store themed icon so it can be passed to dialog box later
		icon = Gtk.Image.new_from_gicon(de_row.themed_icon)
		icon.add_css_class('icon-dropshadow')
		icon.set_pixel_size(64)
		icon.set_margin_top(12)
		icon.set_margin_bottom(12)
		de_row.add_prefix(icon)

		# Add a tag to the row if an amount has been donated to the DE this year
		amount_donated_to_de_this_year = get_amount_donated_to_de_this_year(de_name)
		if amount_donated_to_de_this_year:
			box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
			label_amount = Gtk.Label(label=get_amount_as_locale_str(amount_donated_to_de_this_year, symbol=True))
			label_amount.add_css_class('caption')
			label_amount.add_css_class('bold')
			label_clarifier = Gtk.Label(label='(this year)')
			label_clarifier.add_css_class('subtitle')
			box.append(label_amount)
			box.append(label_clarifier)
			de_row.add_suffix(box)

		de_row.set_activatable(True)
		self.de_box.append(de_row)


		# Open donation dialog box when an app row is clicked
		self.apps_listbox.connect("row-activated", self.on_row_clicked)
		self.de_box.connect("row-activated", self.on_de_row_clicked)

	def on_frequency_changed(self, settings, key):
		self.period = settings.get_string(key)

		self.init_period()
		self.set_period_name()
		self.populate_apps_used_list()

	def init_period(self):
		# from_date is always today so the user always starts with today's period
		self.from_date = date.today()

		if self.period == "weekly":
			# A "week" is Monday to Sunday
			# We set `from_date` to the 1st day of the current week by subtracting whatever `weekday()` (Monday==0)
			# And set `to_date` to 6 days later (which 1st+6=7)
			self.from_date = self.from_date - timedelta(days=self.from_date.weekday())
			self.to_date = self.from_date + timedelta(days=6)

		elif self.period == "monthly":
			self.from_date = self.from_date.replace(day=1)
			# to_date is dependent on how many days in the month - uses calendar.monthrange
			# https://docs.python.org/3/library/calendar.html#calendar.monthrange
			self.to_date = self.from_date.replace(day=monthrange(self.from_date.year, self.from_date.month)[1])

		elif self.period == "yearly":
			self.from_date = self.from_date.replace(day=1, month=1)
			# to_date is 31 December of current year
			self.to_date = self.from_date.replace(day=31, month=12)

		# TODO maybe add infinite in the future. All donations are lumped in the same period.
		# elif self.period == "infinite":
		# 	self.from_date = date.min
		# 	self.to_date = date.max


	def set_period_name(self):
		if self.period == "weekly":
			self.period_name.set_label(f"Week of {self.from_date.strftime(locale.nl_langinfo(locale.D_FMT))}")
		elif self.period == "monthly":
			self.period_name.set_label(self.from_date.strftime("%B %Y"))
		elif self.period == "yearly":
			self.period_name.set_label(str(self.from_date.year))

	def populate_apps_used_list(self):
		# Clear list before populating (not needed first time, but needed all other times)
		self.apps_listbox.remove_all()
		apps_used_list = get_apps_used_list(self.from_date.strftime("%Y-%m-%d"), self.to_date.strftime("%Y-%m-%d"))

		for app in apps_used_list:
			row = Adw.ActionRow(title=app['name'])

			# Add app id to row so it can be used later when saving donations
			row.app_id = app['id']

			# Get icon from desktop file
			desktop_file_name = app['desktop_file'] # e.g. 'geany.desktop'
			app_info = Gio.DesktopAppInfo.new(desktop_file_name)

			# Store themed_icon on row so it can be passed to DonationDialog
			row.themed_icon = app_info.get_icon() # Returns a Gio.ThemedIcon
			if row.themed_icon is None:
				continue

			row_icon = Gtk.Image.new_from_gicon(row.themed_icon)
			# row_icon.set_icon_size(Gtk.IconSize.LARGE)
			row_icon.set_pixel_size(64)
			row_icon.add_css_class('icon-dropshadow')
			row_icon.set_margin_top(12)
			row_icon.set_margin_bottom(12)

			row.add_prefix(row_icon)
			row.set_subtitle(f"{str(app['days_used'])} days")

			# Add a tag to the row if an amount has been donated to the app this year
			if app['amount_donated_this_year']:
				box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
				label_amount = Gtk.Label(label=get_amount_as_locale_str(app['amount_donated_this_year'], symbol=True))
				label_amount.add_css_class('caption')
				label_amount.add_css_class('bold')
				label_clarifier = Gtk.Label(label='(this year)')
				label_clarifier.add_css_class('subtitle')
				box.append(label_amount)
				box.append(label_clarifier)
				row.add_suffix(box)

			row.set_activatable(True)
			self.apps_listbox.append(row)

		# Display the listbox or placeholder StackPage based on whether there are any apps to display
		if apps_used_list:
			self.apps_list_stack.set_visible_child(self.apps_listbox)
		else:
			self.apps_list_stack.set_visible_child(self.apps_placeholder)

	# SIGNAL
	def show_next_period(self, _):
		'''Sets the instance's variables of from_date and to_date to the next period's values, and updates the apps list with records within that range.'''
		if self.period == "weekly":
			self.from_date = self.from_date + timedelta(weeks=1)
			self.to_date = self.to_date + timedelta(weeks=1)

		elif self.period == "monthly":
			self.from_date = self.to_date + timedelta(days=1) # +1 day to get to the next month
			# to_date is dependent on how many days in the month - uses calendar.monthrange to get the number of days in from_date's month
			# https://docs.python.org/3/library/calendar.html#calendar.monthrange
			self.to_date = self.from_date.replace(day=monthrange(self.from_date.year, self.from_date.month)[1])

		elif self.period == "yearly":
			self.from_date = self.to_date + timedelta(days=1) # +1 day to get to the next year
			self.to_date = self.from_date.replace(day=31, month=12) # 31 December of from_date's year

		self.populate_apps_used_list()
		self.set_period_name()

	# SIGNAL
	def show_prev_period(self, _):
		'''Sets the instance's variables of from_date and to_date to the previous period's values, and updates the apps list with records within that range.'''
		if self.period == "weekly":
			self.from_date = self.from_date - timedelta(weeks=1)
			self.to_date = self.to_date - timedelta(weeks=1)

		elif self.period == "monthly":
			self.to_date = self.from_date - timedelta(days=1) # -1 day to get to the last day of the previous month month
			self.from_date = self.to_date.replace(day=1)

		elif self.period == "yearly":
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

	def on_de_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		dialog = DonationDialog(
			app_name = row.get_title(),
			themed_icon = row.themed_icon,
			de=True
		)
		dialog.present(self)
		
