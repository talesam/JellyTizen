# app.py
import gi
import os
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio
from pages.welcome import WelcomePage
from pages.device import DevicePage
from pages.certificates import CertificatesPage
from pages.install import InstallPage
from pages.preferences import PreferencesPage
from utils.config import ConfigManager
from utils.logger import Logger
from utils.constants import *
from utils.i18n import _
from services.docker import DockerService
from services.device import DeviceService
from services.certificates import CertificateService

class JellyTizenApplication(Adw.Application):
    """Main application class for JellyTizen."""

    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

        self.config_manager = ConfigManager()
        self.logger = Logger()
        self.logger.info(f"{APP_NAME} {APP_VERSION} starting")
        self.window = None
        
    def do_activate(self):
        """Called when the application is activated."""
        if not self.window:
            self.window = JellyTizenWindow(application=self, 
                                          config_manager=self.config_manager,
                                          logger=self.logger)
        self.window.present()

class JellyTizenWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, application, config_manager, logger):
        super().__init__(application=application)

        self.config_manager = config_manager
        self.logger = logger

        # Initialize services with logger
        self.docker_service = DockerService(logger=logger)
        self.device_service = DeviceService(logger=logger)
        self.certificate_service = CertificateService(logger=logger)

        self.logger.info("Initializing main window")

        self.set_title(APP_NAME)

        # Get window size from config or use defaults
        window_width = self.config_manager.get('ui.window_width', WINDOW_DEFAULT_WIDTH)
        window_height = self.config_manager.get('ui.window_height', WINDOW_DEFAULT_HEIGHT)
        self.set_default_size(window_width, window_height)

        # Set minimum size
        self.set_resizable(True)  # Allow user to resize manually
        self.set_size_request(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._setup_ui()
        self._setup_actions()
        
    def _setup_ui(self):
        """Setup the main UI components."""
        # Main content
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.content_box)

        # Header bar
        self.header_bar = Adw.HeaderBar()
        self.content_box.append(self.header_bar)

        # Menu button
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(self._create_menu())
        self.header_bar.pack_end(self.menu_button)

        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.content_box.append(self.toast_overlay)

        # Navigation view with scroll control
        self.navigation_view = Adw.NavigationView()
        self.navigation_view.set_vexpand(True)  # Fill available space
        self.toast_overlay.set_child(self.navigation_view)
        
        # Pages
        self.welcome_page = WelcomePage(self)
        self.device_page = DevicePage(self)
        self.certificates_page = CertificatesPage(self)
        self.install_page = InstallPage(self)
        
        # Add welcome page initially
        nav_page = Adw.NavigationPage(child=self.welcome_page, title=_("Welcome"))
        self.navigation_view.add(nav_page)

    def _create_menu(self):
        """Create the main application menu."""
        menu = Gio.Menu()
        menu.append(_("Preferences"), "win.preferences")
        menu.append(_("About"), "win.about")
        return menu
        
    def _setup_actions(self):
        """Setup application actions."""
        # Preferences action
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self._on_preferences)
        self.add_action(preferences_action)
        
        # About action  
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        
    def _on_preferences(self, action, param):
        """Show preferences window."""
        preferences_window = PreferencesPage(self)
        preferences_window.present(self)
        
    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=APP_VERSION,
            developer_name=_("JellyTizen Team"),
            license_type=Gtk.License.GPL_3_0,
            website=APP_GITHUB_URL,
            issue_url=APP_ISSUE_URL,
            copyright=APP_COPYRIGHT
        )
        about.set_developers([_("JellyTizen Contributors")])
        about.present(self)
        
    def navigate_to_page(self, page_widget, title):
        """Navigate to a specific page."""
        nav_page = Adw.NavigationPage(child=page_widget, title=title)
        self.navigation_view.push(nav_page)