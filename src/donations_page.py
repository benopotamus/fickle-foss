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

from datetime import date
from decimal import Decimal
from gi.repository import Adw, Gtk, Gio, GObject

from . import db
from . import helpers
from .donation_dialog import DonationDialog


class Donation(GObject.Object):
	"""Represents one donation row on the Donations page.
	Only `amount` needs to be a GObject property (to make it reactive).
	"""
	__gtype_name__ = 'Donation'

	amount = GObject.Property(type=int, default=0)

	def __init__(self, donation_id, app_id, app_name, donation_date, amount, desktop_file):
		super().__init__(amount=Decimal(amount))
		self.id = donation_id # row.id in db
		self.app_id = app_id # row.id in db
		self.app_name = app_name
		self.date = donation_date  # ISO string e.g. "2026-07-15"
		self.desktop_file = desktop_file # app's desktop file name


def _compare_by_date_desc(donation_a, donation_b):
	"""Sort newest-first within a group, matching db.get_donations_groups' ORDER BY."""
	if donation_a.date == donation_b.date:
		return 0
	return -1 if donation_a.date > donation_b.date else 1


@Gtk.Template(resource_path='/giving/fickle/foss/donation-group.ui')
class DonationGroup(Gtk.Box):
	__gtype_name__ = "DonationGroup"

	heading = Gtk.Template.Child()
	listbox = Gtk.Template.Child()

	def __init__(self, group_name):
		super().__init__()
		self.heading.set_label(group_name)

		self.store = Gio.ListStore.new(Donation)
		self.listbox.bind_model(self.store, self._create_row)
		self.listbox.connect("row-activated", self.on_listbox_row_clicked)

	def add_donation(self, donation):
		self.store.insert_sorted(donation, _compare_by_date_desc)

	def remove_donation(self, donation):
		found, index = self.store.find(donation)
		if found:
			self.store.remove(index)

	def _create_row(self, donation):
		"""Builds the row widget for one Donation. Called automatically by
		self.listbox.bind_model whenever an donation is inserted into self.store."""
		row = Adw.ActionRow(title=donation.app_name)
		# Stashed on the row so on_listbox_row_clicked can get back to the donation that
		# produced it (and DonationsPage can find the right donation/group to update later).
		row.donation = donation

		amount_label = Gtk.Label()
		amount_label.add_css_class('donation-amount')
		donation.bind_property(
			"amount", amount_label, "label",
			GObject.BindingFlags.SYNC_CREATE,
			transform_to=lambda _, amount: helpers.to_money(amount)
		)
		row.add_suffix(amount_label)

		icon_image = helpers.get_app_icon_image(donation.desktop_file, 64)
		icon_image.add_css_class('icon-dropshadow')
		icon_image.set_margin_end(6)
		icon_image.set_margin_top(12)
		icon_image.set_margin_bottom(12)
		row.add_prefix(icon_image)

		row.set_activatable(True)
		return row

	# SIGNAL
	def on_listbox_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		donation = row.donation
		dialog = DonationDialog(
			app_id = donation.app_id,
			donation_id = donation.id,
			desktop_file = donation.desktop_file,
			app_name = donation.app_name,
			donation_date = donation.date,
			donation_amount = donation.amount,
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
		self.donation_freq = self.settings.get_string("donation-frequency") # e.g. "monthly"

		self.period_groups = {} # period key (e.g. "July 2026") -> DonationGroup
		self.donations_by_id = {} # donation id -> (Donation, DonationGroup) - lets `handle_donation_updated` and `handle_donation_deleted`` find a donation's current row without searching every group.

		self.populate_donations()

		self.settings.connect("changed::donation-frequency", self.on_frequency_changed)

	def populate_donations(self):
		"""Deletes and then (re)populates the main donation list.

		Used on startup.
		Also used as a fallback for handle_donation_created/updated/deleted when the creating/updating/deleting results in a group needing to be added (first donation in the group) or deleted (the only donation in a group is removed). New groups or deleting groups requires headings and boxes and things need to be put in the correct order. Doing this full refresh is less complicated than trying to manage all that and it should happen rarely.
		"""

		# Clear page before populating
		while child := self.donation_groups_box.get_first_child():
			self.donation_groups_box.remove(child)
		self.period_groups = {}
		self.donations_by_id = {}

		donation_groups = db.get_donations_groups(self.donation_freq)

		# Show placeholder if no donations yet
		if not donation_groups:
			self.set_visible_child(self.donations_placeholder)
			return

		for group_name, group_rows in donation_groups.items():
			donation_group = DonationGroup(group_name)

			for donation in group_rows:
				donation = Donation(
					donation_id = donation['id'], # row.id in db
					app_id = donation['app_id'], # row.id in db
					app_name = donation['name'],
					donation_date = donation['date'],
					amount = donation['amount'],
					desktop_file = donation['desktop_file'] # app's desktop file name
				)
				donation_group.add_donation(donation)
				self.donations_by_id[donation.id] = (donation, donation_group)

			self.period_groups[group_name] = donation_group
			self.donation_groups_box.append(donation_group)

		# Need to make page visible in case placeholder was being displayed previously
		self.set_visible_child(self.donation_groups_box)

	def handle_donation_created(self, donation_id, app_id, app_name, new_date, amount, desktop_file):
		"""Adds a new donation row.
		Does an in-place add unless it would result in a new group as well, in which case falls back to populate_donations().
		"""
		# No groups at all means this is the first donation ever and the placeholder is
		# showing - the rebuild swaps in donation_groups_box.
		if not self.period_groups:
			self.populate_donations()
			return

		group = self.period_groups.get(helpers.get_period_name(date.fromisoformat(new_date), self.donation_freq))

		if group is None:
			# Falls in a period that has no group yet, so it needs a new heading inserted
			# at the right point in donation_groups_box - only a rebuild gets that order right.
			self.populate_donations()
			return

		donation = Donation(
			donation_id = donation_id,
			app_id = app_id,
			app_name = app_name,
			donation_date = new_date,
			amount = amount,
			desktop_file = desktop_file
		)
		# add_donation uses insert_sorted, so the row lands in the right place within the
		# group and bind_model builds the widget - nothing to touch directly here.
		group.add_donation(donation)
		self.donations_by_id[donation.id] = (donation, group)

	def handle_donation_updated(self, donation_id, new_date, new_amount):
		"""Updates a donation row.
		Does an in-place update unless it would result in a new group being created or an existing group being deleted (because the donation changed date and it was the only one in the existing group). For these complex situations, falls back to populate_donations().
		"""
		donation, group = self.donations_by_id.get(donation_id)
		new_key = helpers.get_period_name(date.fromisoformat(new_date), self.donation_freq)
		old_key = helpers.get_period_name(date.fromisoformat(donation.date), self.donation_freq)

		if new_key == old_key:
			# Same period group - no rows move, just update the values in place.
			# donation.amount is bound to the row's label, so this alone updates the UI.
			donation.date = new_date
			donation.amount = new_amount
			return

		target_group = self.period_groups.get(new_key)
		source_would_become_empty = group.store.get_n_items() == 1

		if target_group is None or source_would_become_empty:
			self.populate_donations()
			return

		# Move: remove from the old group's store, update the donation, insert into the
		# new group's store in the right sorted position. Both listboxes update
		# themselves via bind_model - no row widgets are touched directly here.
		group.remove_donation(donation)
		donation.date = new_date
		donation.amount = new_amount
		target_group.add_donation(donation)
		self.donations_by_id[donation_id] = (donation, target_group)

	def handle_donation_deleted(self, donation_id):
		"""Deletes a new donation row.
		Does an in-place update unless it would result in a group being deleted (because the donation changed date and it was the only one in the existing group). For these complex situations, falls back to populate_donations().
		"""
		donation, group = self.donations_by_id.get(donation_id)

		if group.store.get_n_items() == 1:
			self.populate_donations()
			return

		group.remove_donation(donation)
		del self.donations_by_id[donation_id]

	def on_frequency_changed(self, settings, key):
		self.donation_freq = settings.get_string(key)
		self.populate_donations()
