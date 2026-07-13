# donations_page.py
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
from gi.repository import Adw, Gtk, Gio

from .db import get_donations_groups
from .helpers import get_de_name_and_icon, get_amount_as_locale_str
from .donation_dialog import DonationDialog


@Gtk.Template(resource_path='/giving/fickle/foss/donation-group.ui')
class DonationGroup(Gtk.Box):
	__gtype_name__ = "DonationGroup"

	heading = Gtk.Template.Child()
	listbox = Gtk.Template.Child()

	def __init__(self, group_name):
		super().__init__()
		self.heading.set_label(group_name)

		# Open donation dialog box when a donation row is clicked
		self.listbox.connect("row-activated", self.on_listbox_row_clicked)

	def add_row(self, row):
		self.listbox.append(row)

	# SIGNAL
	def on_listbox_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		dialog = DonationDialog(
			donation_id = row.id,
			app_name = row.get_title(),
			themed_icon = row.themed_icon,
			donation_date = row.donation_date,
			donation_amount = row.amount,
		)
		dialog.present(self)


@Gtk.Template(resource_path='/giving/fickle/foss/donations-page.ui')
class DonationsPage(Gtk.Stack):
	__gtype_name__ = 'DonationsPage'
	donation_groups_box = Gtk.Template.Child()
	donations_placeholder = Gtk.Template.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.period = self.settings.get_string("donation-frequency") # e.g. "monthly"

		self.populate_donations()

		self.settings.connect("changed::donation-frequency", self.on_frequency_changed)

		# This realize stuff is my shameful hack to get the donations list to refresh when a donation is updated
		# It uses a signal defined in window.py
		# donation_dialog.py emits it when a successful save occurs and that save it updating an existing donation
		self.connect('realize', self.on_realize)

	def on_realize(self, _):
		self.get_root().connect('donation-updated', self._refresh_donations)
		self.get_root().connect('donation-deleted', self._refresh_donations)
	def _refresh_donations(self, _): self.populate_donations()


	def populate_donations(self):
		"""Populates the main donation list, creating AdwPreferenceGroups for each period and AdwActionRows for each donation."""
		# Clear page before populating (not needed first time, but needed all other times, in case data is changed in database)
		# TODO look at using ListStore instead
		while child := self.donation_groups_box.get_first_child():
			self.donation_groups_box.remove(child)

		donation_groups = get_donations_groups(self.period)

		# Show placeholder if no donations yet
		# TODO Check that this works. It will need fixing if db isn't returning none when there are no donations at all
		if not donation_groups:
			self.set_visible_child(self.donations_placeholder)
			return

		for group_name, group in donation_groups.items():
			donation_group = DonationGroup(group_name)

			for donation in group:
				row = Adw.ActionRow(title=donation['name'])

				# Store some donation values on row so they can be passed to the donation dialog when editing
				row.id = donation['id']
				row.donation_date = donation['date']
				row.amount = get_amount_as_locale_str(donation['amount'], symbol=False)
				amount_with_symbol = get_amount_as_locale_str(donation['amount'], symbol=True)
				label = Gtk.Label(label=amount_with_symbol)
				label.add_css_class('donation-amount')
				row.add_suffix(label)

				# Get icon
				# Special case for DE
				if donation['desktop_file'] == 'DE':
					_, row.themed_icon = get_de_name_and_icon()
				else:
					# Otherwise use desktop file
					app_info = Gio.DesktopAppInfo.new(donation['desktop_file'])
					# Store themed_icon on row so it can be passed to DonationDialog
					row.themed_icon = app_info.get_icon() # Returns a Gio.ThemedIcon
					if row.themed_icon is None:
						continue

				row_icon = Gtk.Image.new_from_gicon(row.themed_icon)

				# row_icon.set_icon_size(Gtk.IconSize.LARGE)
				row_icon.set_pixel_size(64)
				row_icon.add_css_class('icon-dropshadow')
				row_icon.set_margin_end(6)
				row_icon.set_margin_top(12)
				row_icon.set_margin_bottom(12)
				row.add_prefix(row_icon)

				row.set_activatable(True)
				donation_group.add_row(row)

			self.donation_groups_box.append(donation_group)

		# Need to make page visible in case placeholder was being displayed previously
		self.set_visible_child(self.donation_groups_box)


	def on_frequency_changed(self, settings, key):
		self.period = settings.get_string(key)
		self.populate_donations()
