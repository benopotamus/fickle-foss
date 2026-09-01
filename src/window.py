# window.py
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

from gi.repository import Adw, Gtk, Gio, GObject

from . import helpers
from .donate_page import DonatePage # Used by @Gtk.Template
from .donations_page import DonationsPage # Used by @Gtk.Template


@Gtk.Template(resource_path='/giving/fickle/foss/window.ui')
class FickleFossWindow(Adw.ApplicationWindow):
	__gtype_name__ = 'FickleFossWindow'
	stack = Gtk.Template.Child()
	donations_page = Gtk.Template.Child()
	donate_page = Gtk.Template.Child()
	budget_label = Gtk.Template.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		# Sync window properties with Gio.Settings
		self.settings = Gio.Settings(schema_id="giving.fickle.foss")
		self.settings.bind("window-width", self, "default-width", Gio.SettingsBindFlags.DEFAULT)
		self.settings.bind("window-height", self, "default-height", Gio.SettingsBindFlags.DEFAULT)
		self.settings.bind("window-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT)
		self.settings.bind("window-fullscreen", self, "fullscreened", Gio.SettingsBindFlags.DEFAULT)

		store = Gio.Application.get_default().store # AppStateStore instance from state.py
		# https://api.pygobject.gnome.org/GObject-2.0/class-Object.html#methods
		store.bind_property(
			"budget-remaining", # source property
			self.budget_label, # target object
			"label", # target property
			GObject.BindingFlags.SYNC_CREATE,
			transform_to = self.get_budget_label_text
		)

		# TODO If Fickle FOSS doesn't have access to the /usr/share/applications directory, AND Fickle FOSS Tracker extension isn't running, pop up a dialog box telling the user about the need for the extension. Include a link to Tracker's page on extensions.gnome.org so user can easily install it
	
	def get_budget_label_text(self, _, amount):
		if amount < 0:
			self.budget_label.add_css_class("warning")
			return f"{helpers.to_money(-amount)} over budget"
		else:
			self.budget_label.remove_css_class("warning")
			return f"{helpers.to_money(amount)} remaining in budget"



	def on_page_changed(self, stack, _):
		visible_child_name = stack.get_visible_child_name()
		if visible_child_name == 'donations':
			self.donations_page.populate_donations()
		elif visible_child_name == 'donate':
			self.donate_page.populate_apps_used_list()
