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


class DonationItem(GObject.Object):
	"""Represents one donation row on the Donations page.
	Only `amount` needs to be a GObject property (to make it reactive).
	"""
	__gtype_name__ = 'DonationItem'

	amount = GObject.Property(type=int, default=0)

	def __init__(self, donation_id, app_id, app_name, donation_date, amount, desktop_file):
		super().__init__(amount=Decimal(amount))
		self.id = donation_id # row.id in db
		self.app_id = app_id # row.id in db
		self.app_name = app_name
		self.date = donation_date  # ISO string e.g. "2026-07-15"
		self.desktop_file = desktop_file # app's desktop file name


def _compare_by_date_desc(item_a, item_b):
	"""Sort newest-first within a group, matching db.get_donations_groups' ORDER BY."""
	if item_a.date == item_b.date:
		return 0
	return -1 if item_a.date > item_b.date else 1


@Gtk.Template(resource_path='/giving/fickle/foss/donation-group.ui')
class DonationGroup(Gtk.Box):
	__gtype_name__ = "DonationGroup"

	heading = Gtk.Template.Child()
	listbox = Gtk.Template.Child()

	def __init__(self, group_name):
		super().__init__()
		self.heading.set_label(group_name)

		self.store = Gio.ListStore.new(DonationItem)
		self.listbox.bind_model(self.store, self._create_row)
		self.listbox.connect("row-activated", self.on_listbox_row_clicked)

	def add_item(self, item):
		self.store.insert_sorted(item, _compare_by_date_desc)

	def remove_item(self, item):
		found, index = self.store.find(item)
		if found:
			self.store.remove(index)

	def _create_row(self, item):
		"""Builds the row widget for one DonationItem. Called automatically by
		self.listbox.bind_model whenever an item is inserted into self.store."""
		row = Adw.ActionRow(title=item.app_name)
		# Stashed on the row so on_listbox_row_clicked can get back to the item that
		# produced it (and DonationsPage can find the right item/group to update later).
		row.donation_item = item

		amount_label = Gtk.Label()
		amount_label.add_css_class('donation-amount')
		item.bind_property(
			"amount", amount_label, "label",
			GObject.BindingFlags.SYNC_CREATE,
			transform_to=lambda _, amount: helpers.to_money(amount)
		)
		row.add_suffix(amount_label)

		icon_image = helpers.get_app_icon_image(item.desktop_file, 64)
		icon_image.add_css_class('icon-dropshadow')
		icon_image.set_margin_end(6)
		icon_image.set_margin_top(12)
		icon_image.set_margin_bottom(12)
		row.add_prefix(icon_image)

		row.set_activatable(True)
		return row

	# SIGNAL
	def on_listbox_row_clicked(self, listbox:Gtk.ListBox, row:Gtk.ListBoxRow):
		item = row.donation_item
		dialog = DonationDialog(
			app_id = item.app_id,
			donation_id = item.id,
			desktop_file = item.desktop_file,
			app_name = item.app_name,
			donation_date = item.date,
			donation_amount = item.amount,
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

		self.period_groups = {}   # period key (e.g. "July 2026") -> DonationGroup
		self.items_by_id = {}     # donation id -> (DonationItem, DonationGroup) - lets
		                          # handle_donation_updated/deleted find a donation's
		                          # current row without searching every group.

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
		self.items_by_id = {}

		donation_groups = db.get_donations_groups(self.donation_freq)

		# Show placeholder if no donations yet
		if not donation_groups:
			self.set_visible_child(self.donations_placeholder)
			return

		for group_name, group_rows in donation_groups.items():
			donation_group = DonationGroup(group_name)

			for donation in group_rows:
				item = DonationItem(
					donation_id = donation['id'], # row.id in db
					app_id = donation['app_id'], # row.id in db
					app_name = donation['name'],
					donation_date = donation['date'],
					amount = donation['amount'],
					desktop_file = donation['desktop_file'] # app's desktop file name
				)
				donation_group.add_item(item)
				self.items_by_id[item.id] = (item, donation_group)

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

		item = DonationItem(
			donation_id = donation_id,
			app_id = app_id,
			app_name = app_name,
			donation_date = new_date,
			amount = amount,
			desktop_file = desktop_file
		)
		# add_item uses insert_sorted, so the row lands in the right place within the
		# group and bind_model builds the widget - nothing to touch directly here.
		group.add_item(item)
		self.items_by_id[item.id] = (item, group)

	def handle_donation_updated(self, donation_id, new_date, new_amount):
		"""Updates a donation row.
		Does an in-place update unless it would result in a new group being created or an existing group being deleted (because the donation changed date and it was the only one in the existing group). For these complex situations, falls back to populate_donations().
		"""
		item, group = self.items_by_id.get(donation_id)
		new_key = helpers.get_period_name(date.fromisoformat(new_date), self.donation_freq)
		old_key = helpers.get_period_name(date.fromisoformat(item.date), self.donation_freq)

		if new_key == old_key:
			# Same period group - no rows move, just update the values in place.
			# item.amount is bound to the row's label, so this alone updates the UI.
			item.date = new_date
			item.amount = new_amount
			return

		target_group = self.period_groups.get(new_key)
		source_would_become_empty = group.store.get_n_items() == 1

		if target_group is None or source_would_become_empty:
			self.populate_donations()
			return

		# Move: remove from the old group's store, update the item, insert into the
		# new group's store in the right sorted position. Both listboxes update
		# themselves via bind_model - no row widgets are touched directly here.
		group.remove_item(item)
		item.date = new_date
		item.amount = new_amount
		target_group.add_item(item)
		self.items_by_id[donation_id] = (item, target_group)

	def handle_donation_deleted(self, donation_id):
		"""Deletes a new donation row.
		Does an in-place update unless it would result in a group being deleted (because the donation changed date and it was the only one in the existing group). For these complex situations, falls back to populate_donations().
		"""
		entry = self.items_by_id.get(donation_id)
		if entry is None:
			self.populate_donations()
			return
		item, group = entry

		if group.store.get_n_items() == 1:
			self.populate_donations()
			return

		group.remove_item(item)
		del self.items_by_id[donation_id]

	def on_frequency_changed(self, settings, key):
		self.donation_freq = settings.get_string(key)
		self.populate_donations()
