# pages/install.py
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Vte', '3.91')

from gi.repository import Gtk, Adw, Vte, GLib, Pango
from services.docker import DockerService
from services.device import DeviceService
from utils.i18n import _

class InstallPage(Gtk.Box):
    """Installation progress page with terminal output."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)

        self.window = window
        self.docker_service = DockerService(logger=window.logger)
        self.device_service = DeviceService(logger=window.logger)
        
        self.installation_running = False
        self.current_step = 0
        self.total_steps = 6
        
        self.set_margin_top(48)
        self.set_margin_bottom(48)
        self.set_margin_start(48)
        self.set_margin_end(48)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the installation page UI."""
        # Header
        header_group = Adw.PreferencesGroup()
        header_group.set_title(_("Jellyfin Installation"))
        header_group.set_description(_("Installing Jellyfin on your Samsung Tizen device"))
        self.append(header_group)

        # Progress section
        self.progress_group = Adw.PreferencesGroup()
        self.progress_group.set_title(_("Installation Progress"))
        self.append(self.progress_group)

        # Progress bar
        self.progress_row = Adw.ActionRow()
        self.progress_row.set_title(_("Overall Progress"))
        self.progress_row.set_subtitle(_("Ready to start installation"))
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_valign(Gtk.Align.CENTER)
        self.progress_row.add_suffix(self.progress_bar)
        
        self.progress_group.add(self.progress_row)
        
        # Current step
        self.step_row = Adw.ActionRow()
        self.step_row.set_title(_("Current Step"))
        self.step_row.set_subtitle(_("Waiting to start..."))
        self.progress_group.add(self.step_row)

        # Terminal section
        self.terminal_group = Adw.PreferencesGroup()
        self.terminal_group.set_title(_("Installation Log"))
        self.terminal_group.set_description(_("Detailed output from the installation process"))
        self.append(self.terminal_group)
        
        # Terminal widget
        self.terminal_frame = Gtk.Frame()
        self.terminal_frame.set_size_request(-1, 300)
        
        self.terminal = Vte.Terminal()
        self.terminal.set_font(Pango.FontDescription("monospace 10"))
        self.terminal.set_scroll_on_output(True)
        self.terminal.set_scrollback_lines(1000)
        
        # Terminal scrolled window
        self.terminal_scroll = Gtk.ScrolledWindow()
        self.terminal_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.terminal_scroll.set_child(self.terminal)
        
        self.terminal_frame.set_child(self.terminal_scroll)
        self.terminal_group.add(self.terminal_frame)
        
        # Actions
        self.actions_group = Adw.PreferencesGroup()
        self.append(self.actions_group)

        # Start installation button
        start_row = Adw.ActionRow()
        start_row.set_title(_("Start Installation"))
        start_row.set_subtitle(_("Begin the Jellyfin installation process"))

        self.start_button = Gtk.Button.new_with_label(_("Start Installation"))
        self.start_button.set_valign(Gtk.Align.CENTER)
        self.start_button.add_css_class("suggested-action")
        self.start_button.connect("clicked", self._on_start_installation)
        start_row.add_suffix(self.start_button)

        self.actions_group.add(start_row)

        # Cancel/Close button
        self.cancel_row = Adw.ActionRow()
        self.cancel_row.set_title(_("Cancel Installation"))
        self.cancel_row.set_subtitle(_("Stop the current installation process"))

        self.cancel_button = Gtk.Button.new_with_label(_("Cancel"))
        self.cancel_button.set_valign(Gtk.Align.CENTER)
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.set_sensitive(False)
        self.cancel_button.connect("clicked", self._on_cancel_installation)
        self.cancel_row.add_suffix(self.cancel_button)

        self.actions_group.add(self.cancel_row)

        # Success actions (initially hidden)
        self.success_group = Adw.PreferencesGroup()
        self.success_group.set_title(_("Installation Complete"))
        self.success_group.set_visible(False)
        self.append(self.success_group)

        success_row = Adw.ActionRow()
        success_row.set_title(_("Installation Successful!"))
        success_row.set_subtitle(_("Jellyfin has been installed on your device"))

        finish_button = Gtk.Button.new_with_label(_("Finish"))
        finish_button.set_valign(Gtk.Align.CENTER)
        finish_button.add_css_class("suggested-action")
        finish_button.connect("clicked", self._on_finish)
        success_row.add_suffix(finish_button)
        
        self.success_group.add(success_row)
        
    def _on_start_installation(self, button):
        """Start the installation process."""
        if self.installation_running:
            return
            
        self.installation_running = True
        self.current_step = 0
        
        # Update UI
        self.start_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.success_group.set_visible(False)
        
        # Clear terminal
        self.terminal.reset(True, True)
        
        # Start installation steps
        self._run_installation_steps()
        
    def _run_installation_steps(self):
        """Run the installation steps sequentially."""
        steps = [
            (_("Preparing Docker environment"), self._step_prepare_docker),
            (_("Downloading Tizen SDK"), self._step_download_sdk),
            (_("Setting up certificates"), self._step_setup_certificates),
            (_("Building Jellyfin app"), self._step_build_app),
            (_("Connecting to device"), self._step_connect_device),
            (_("Installing application"), self._step_install_app),
        ]
        
        def run_next_step():
            if self.current_step >= len(steps) or not self.installation_running:
                if self.installation_running:
                    self._installation_complete()
                return
                
            step_name, step_func = steps[self.current_step]
            self._update_progress(step_name)
            
            def on_step_complete(success, message=""):
                if not self.installation_running:
                    return
                    
                if success:
                    self.current_step += 1
                    GLib.idle_add(run_next_step)
                else:
                    self._installation_failed(message)
                    
            step_func(on_step_complete)
            
        run_next_step()
        
    def _update_progress(self, step_name):
        """Update progress display."""
        progress = self.current_step / self.total_steps
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{self.current_step}/{self.total_steps}")

        self.progress_row.set_subtitle(_("Step {current} of {total}").format(current=self.current_step + 1, total=self.total_steps))
        self.step_row.set_subtitle(step_name)
        
        # Log to terminal
        self._log_to_terminal(f"\n=== {step_name} ===\n")
        
    def _step_prepare_docker(self, callback):
        """Prepare Docker environment."""
        self._log_to_terminal(_("Checking Docker status...") + "\n")

        def on_docker_ready(success, message):
            if success:
                self._log_to_terminal(_("Docker environment ready") + "\n")
            else:
                self._log_to_terminal(_("Docker error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.docker_service.prepare_environment_async(on_docker_ready)

    def _step_download_sdk(self, callback):
        """Download and setup Tizen SDK."""
        self._log_to_terminal(_("Downloading Tizen SDK...") + "\n")

        def on_sdk_ready(success, message):
            if success:
                self._log_to_terminal(_("Tizen SDK ready") + "\n")
            else:
                self._log_to_terminal(_("SDK error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.docker_service.setup_tizen_sdk_async(on_sdk_ready)

    def _step_setup_certificates(self, callback):
        """Setup certificates in Docker environment."""
        self._log_to_terminal(_("Setting up certificates...") + "\n")
        
        author_cert = self.window.config_manager.get('certificates.author_cert_path')
        dist_cert = self.window.config_manager.get('certificates.distributor_cert_path')
        password = self.window.config_manager.get('certificates.password')
        
        def on_certs_ready(success, message):
            if success:
                self._log_to_terminal(_("Certificates configured") + "\n")
            else:
                self._log_to_terminal(_("Certificate error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.docker_service.setup_certificates_async(
            author_cert, dist_cert, password, on_certs_ready
        )

    def _step_build_app(self, callback):
        """Build the Jellyfin application."""
        self._log_to_terminal(_("Building Jellyfin application...") + "\n")

        def on_build_complete(success, message):
            if success:
                self._log_to_terminal(_("Application built successfully") + "\n")
            else:
                self._log_to_terminal(_("Build error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.docker_service.build_jellyfin_app_async(on_build_complete)

    def _step_connect_device(self, callback):
        """Connect to the target device."""
        self._log_to_terminal(_("Connecting to device...") + "\n")

        device_ip = self.window.config_manager.get('device.ip')
        dev_mode = self.window.config_manager.get('device.developer_mode', False)

        def on_device_connected(success, message):
            if success:
                self._log_to_terminal(_("Device connected successfully") + "\n")
            else:
                self._log_to_terminal(_("Connection error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.device_service.connect_device_async(device_ip, dev_mode, on_device_connected)

    def _step_install_app(self, callback):
        """Install the application on the device."""
        self._log_to_terminal(_("Installing Jellyfin on device...") + "\n")

        def on_install_complete(success, message):
            if success:
                self._log_to_terminal(_("Installation completed successfully!") + "\n")
            else:
                self._log_to_terminal(_("Installation error: {message}").format(message=message) + "\n")
            callback(success, message)

        self.docker_service.install_app_on_device_async(on_install_complete)
        
    def _log_to_terminal(self, text):
        """Log text to the terminal widget."""
        self.terminal.feed(text.encode('utf-8'))
        
    def _installation_complete(self):
        """Handle successful installation completion."""
        self.installation_running = False

        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text(_("Complete"))
        self.progress_row.set_subtitle(_("Installation completed successfully"))
        self.step_row.set_subtitle(_("All steps completed"))

        self.start_button.set_label(_("Install Again"))
        self.start_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.success_group.set_visible(True)

        self._log_to_terminal("\n=== " + _("Installation Complete!") + " ===\n")
        self._log_to_terminal(_("Jellyfin has been successfully installed on your device.") + "\n")
        self._log_to_terminal(_("You can now launch Jellyfin from your TV's app menu.") + "\n")

    def _installation_failed(self, message):
        """Handle installation failure."""
        self.installation_running = False

        self.progress_row.set_subtitle(_("Installation failed"))
        self.step_row.set_subtitle(_("Error: {message}").format(message=message))

        self.start_button.set_label(_("Retry Installation"))
        self.start_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)

        self._log_to_terminal("\n=== " + _("Installation Failed") + " ===\n")
        self._log_to_terminal(_("Error: {message}").format(message=message) + "\n")

    def _on_cancel_installation(self, button):
        """Cancel the ongoing installation."""
        if self.installation_running:
            self.installation_running = False

            # Stop any running Docker processes
            self.docker_service.stop_all_processes()

            self.progress_row.set_subtitle(_("Installation cancelled"))
            self.step_row.set_subtitle(_("Cancelled by user"))

            self.start_button.set_label(_("Start Installation"))
            self.start_button.set_sensitive(True)
            self.cancel_button.set_sensitive(False)

            self._log_to_terminal("\n=== " + _("Installation Cancelled") + " ===\n")
            
    def _on_finish(self, button):
        """Finish and return to main menu."""
        # Could navigate back to welcome or close application
        pass