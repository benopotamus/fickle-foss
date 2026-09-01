# main.py Hi!
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

import sys
import gi
import locale

from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, Gdk

from .window import FickleFossWindow
from .preferences_dialog import PreferencesDialog
from .state import AppStateStore


class FickleFossApplication(Adw.Application):
	"""The main application singleton class."""

	def __init__(self):
		super().__init__(application_id='giving.fickle.foss',
						 flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
						 resource_base_path='/giving/fickle/foss')
		self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
		self.create_action('about', self.on_about_action)
		self.create_action('preferences', self.on_preferences_action)

		# Single source of truth for donation totals that need to update live in the UI.
		# Created here (rather than on the window) because DonatePage/DonationsPage are
		# built as template children of the window and need this during their own
		# __init__ - reachable anywhere via Gio.Application.get_default().store
		self.store = AppStateStore()

		# Used for currency symbols and date formats
		locale.setlocale(locale.LC_ALL, '')
		# locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8') # Uncomment to test a different locale

		# Setup CSS
		css_provider = Gtk.CssProvider()
		css_provider.load_from_resource('/giving/fickle/foss/styles.css')
		Gtk.StyleContext.add_provider_for_display(
			Gdk.Display.get_default(),
			css_provider,
			Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
		)


	def do_activate(self):
		"""Called when the application is activated.

		We raise the application's main window, creating it if
		necessary.
		"""
		win = self.props.active_window
		if not win:
			win = FickleFossWindow(application=self)
		win.present()

	def on_about_action(self, *args):
		"""Callback for the app.about action."""
		about = Adw.AboutDialog(application_name='Fickle FOSS',
								application_icon='giving.fickle.foss',
								developer_name='ben',
								version='0.1.0',
								translator_credits = _('benopotamus'),
								developers=['ben'],
								copyright='© 2026 Ben Michie')
		about.present(self.props.active_window)

	def on_preferences_action(self, widget, _):
		"""Callback for the app.preferences action."""
		dialog = PreferencesDialog()
		dialog.present(self.props.active_window)

	def create_action(self, name, callback, shortcuts=None):
		"""Add an application action.

		Args:
			name: the name of the action
			callback: the function to be called when the action is
			  activated
			shortcuts: an optional list of accelerators
		"""
		action = Gio.SimpleAction.new(name, None)
		action.connect("activate", callback)
		self.add_action(action)
		if shortcuts:
			self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
	"""The application's entry point."""
	app = FickleFossApplication()
	return app.run(sys.argv)
