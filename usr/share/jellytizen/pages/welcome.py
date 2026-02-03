# pages/welcome.py
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
from services.docker import DockerService
from utils.i18n import _
from utils.ui_helpers import ErrorNotification

class WelcomePage(Gtk.Box):
    """Welcome page with Docker verification - simplified layout."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.window = window
        self.docker_service = DockerService(logger=window.logger)
        
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        self._setup_ui()
        self._check_dependencies()
        
    def _setup_ui(self):
        """Setup the welcome page UI."""
        # Create a clamp to center content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_tightening_threshold(500)
        clamp.set_margin_top(32)
        clamp.set_margin_bottom(32)
        clamp.set_margin_start(32)
        clamp.set_margin_end(32)
        self.append(clamp)
        
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=32)
        clamp.set_child(main_box)
        
        # ============================================
        # HEADER
        # ============================================
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        header_box.set_halign(Gtk.Align.CENTER)
        header_box.set_margin_top(24)
        header_box.set_margin_bottom(24)
        main_box.append(header_box)
        
        # Icon - larger
        icon = Gtk.Image.new_from_icon_name("tv-symbolic")
        icon.set_pixel_size(96)
        icon.add_css_class("dim-label")
        header_box.append(icon)
        
        # Title - larger
        title = Gtk.Label(label=_("JellyTizen Installer"))
        title.add_css_class("title-1")
        header_box.append(title)
        
        # Description
        desc = Gtk.Label(label=_("Install Jellyfin on your Samsung Smart TV or projector"))
        desc.add_css_class("dim-label")
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        header_box.append(desc)
        
        # ============================================
        # REQUIREMENTS - In same flow
        # ============================================
        self.requirements_group = Adw.PreferencesGroup()
        self.requirements_group.set_title(_("System Requirements"))
        main_box.append(self.requirements_group)

        # Docker status row
        self.docker_row = Adw.ActionRow()
        self.docker_row.set_title(_("Docker Engine"))
        self.docker_row.set_subtitle(_("Checking..."))
        
        self.docker_spinner = Gtk.Spinner()
        self.docker_spinner.start()
        self.docker_row.add_suffix(self.docker_spinner)
        
        self.requirements_group.add(self.docker_row)
        
        # Install Docker row (initially not added)
        self.install_docker_row = Adw.ActionRow()
        self.install_docker_row.set_title(_("Install Docker"))
        self.install_docker_row.set_subtitle(_("Docker is required but not installed"))

        self.install_docker_button = Gtk.Button.new_with_label(_("Install"))
        self.install_docker_button.set_valign(Gtk.Align.CENTER)
        self.install_docker_button.add_css_class("suggested-action")
        self.install_docker_button.connect("clicked", self._on_install_docker)
        self.install_docker_row.add_suffix(self.install_docker_button)

        # ============================================
        # CONTINUE BUTTON
        # ============================================
        self.actions_group = Adw.PreferencesGroup()
        main_box.append(self.actions_group)

        self.continue_row = Adw.ActionRow()
        self.continue_row.set_title(_("Continue"))
        self.continue_row.set_subtitle(_("Configure your Samsung TV"))

        self.continue_button = Gtk.Button.new_with_label(_("Continue"))
        self.continue_button.set_valign(Gtk.Align.CENTER)
        self.continue_button.add_css_class("suggested-action")
        self.continue_button.set_sensitive(False)
        self.continue_button.connect("clicked", self._on_continue)
        self.continue_row.add_suffix(self.continue_button)
        
        self.actions_group.add(self.continue_row)
        
    def _check_dependencies(self):
        """Check if all required dependencies are installed."""
        GLib.timeout_add(500, self._check_docker_status)
        
    def _check_docker_status(self):
        """Check Docker installation and status."""
        try:
            is_installed = self.docker_service.is_docker_installed()
            is_running = self.docker_service.is_docker_running() if is_installed else False
            
            self.docker_spinner.stop()
            self.docker_row.remove(self.docker_spinner)
            
            if is_installed and is_running:
                # Docker is ready
                success_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                success_icon.add_css_class("success")
                self.docker_row.add_suffix(success_icon)
                self.docker_row.set_subtitle(_("Ready"))
                self.continue_button.set_sensitive(True)

            elif is_installed and not is_running:
                # Docker installed but not running
                warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
                self.docker_row.add_suffix(warning_icon)
                self.docker_row.set_subtitle(_("Not running"))

                start_button = Gtk.Button.new_with_label(_("Start"))
                start_button.set_valign(Gtk.Align.CENTER)
                start_button.connect("clicked", self._on_start_docker)
                self.docker_row.add_suffix(start_button)

            else:
                # Docker not installed
                error_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
                self.docker_row.add_suffix(error_icon)
                self.docker_row.set_subtitle(_("Not installed"))
                self.requirements_group.add(self.install_docker_row)
                
        except Exception as e:
            self.window.logger.error(f"Error checking Docker status: {e}")
            
        return False
        
    def _on_install_docker(self, button):
        """Handle Docker installation."""
        install_dialog = DockerInstallDialog(self.window)
        install_dialog.present(self.window)
        
    def _on_start_docker(self, button):
        """Handle starting Docker service."""
        button.set_sensitive(False)
        spinner = Gtk.Spinner()
        spinner.start()
        self.docker_row.add_suffix(spinner)

        def on_docker_started(success):
            button.set_sensitive(True)
            self.docker_row.remove(spinner)
            if success:
                self._check_docker_status()

        self.docker_service.start_docker_async(on_docker_started)
        
    def _on_continue(self, button):
        """Navigate to device setup page."""
        self.window.navigate_to_page(self.window.device_page, _("Device Setup"))

class DockerInstallDialog(Adw.AlertDialog):
    """Dialog for Docker installation guidance."""

    def __init__(self, window):
        super().__init__()

        self.window = window
        self.set_heading(_("Install Docker"))
        self.set_body(_("Select your distribution:"))

        self.add_response("cancel", _("Cancel"))
        self.add_response("arch", _("Arch/Manjaro"))
        self.add_response("debian", _("Debian/Ubuntu"))
        self.add_response("fedora", _("Fedora/RHEL"))
        
        self.set_default_response("cancel")
        self.connect("response", self._on_response)
        
    def _on_response(self, dialog, response):
        """Handle dialog response."""
        if response != "cancel":
            try:
                docker_service = DockerService(logger=self.window.logger)
                docker_service.install_docker(response)
            except Exception as e:
                self.window.logger.error(f"Error installing Docker: {e}")
                ErrorNotification.show_error_dialog(
                    self.window, _("Error"), str(e)
                )

        self.close()