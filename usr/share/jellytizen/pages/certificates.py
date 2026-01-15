# pages/certificates.py
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio
from services.certificates import CertificateService
from utils.i18n import _
from utils.ui_helpers import ErrorNotification

class CertificatesPage(Gtk.Box):
    """Certificate management page."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)

        self.window = window
        self.cert_service = CertificateService(logger=window.logger)
        
        self.set_margin_top(48)
        self.set_margin_bottom(48)
        self.set_margin_start(48)
        self.set_margin_end(48)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the certificates page UI."""
        # Header
        header_group = Adw.PreferencesGroup()
        header_group.set_title(_("Developer Certificates"))
        header_group.set_description(_("Configure Samsung developer certificates for app installation"))
        self.append(header_group)

        # Certificate files section
        self.files_group = Adw.PreferencesGroup()
        self.files_group.set_title(_("Certificate Files"))
        self.files_group.set_description(_("Upload your Samsung developer certificate files"))
        self.append(self.files_group)

        # Author certificate
        self.author_cert_row = Adw.ActionRow()
        self.author_cert_row.set_title(_("Author Certificate"))
        self.author_cert_row.set_subtitle(_("author.p12 - Your developer certificate"))

        self.author_cert_button = Gtk.Button.new_with_label(_("Browse"))
        self.author_cert_button.set_valign(Gtk.Align.CENTER)
        self.author_cert_button.connect("clicked", lambda b: self._browse_file("author"))
        self.author_cert_row.add_suffix(self.author_cert_button)
        
        self.files_group.add(self.author_cert_row)
        
        # Distributor certificate
        self.dist_cert_row = Adw.ActionRow()
        self.dist_cert_row.set_title(_("Distributor Certificate"))
        self.dist_cert_row.set_subtitle(_("distributor.p12 - Samsung's distributor certificate"))

        self.dist_cert_button = Gtk.Button.new_with_label(_("Browse"))
        self.dist_cert_button.set_valign(Gtk.Align.CENTER)
        self.dist_cert_button.connect("clicked", lambda b: self._browse_file("distributor"))
        self.dist_cert_row.add_suffix(self.dist_cert_button)

        self.files_group.add(self.dist_cert_row)

        # Password section
        self.password_group = Adw.PreferencesGroup()
        self.password_group.set_title(_("Certificate Password"))
        self.password_group.set_description(_("Enter the password for your author certificate"))
        self.append(self.password_group)

        # Password entry
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title(_("Certificate Password"))
        self.password_row.set_text(self.window.config_manager.get('certificates.password', ''))
        self.password_row.connect("changed", self._on_password_changed)
        self.password_group.add(self.password_row)

        # Profile section
        self.profile_group = Adw.PreferencesGroup()
        self.profile_group.set_title(_("Developer Profile"))
        self.profile_group.set_description(_("Configure your developer profile information"))
        self.append(self.profile_group)

        # Profile name
        self.profile_name_row = Adw.EntryRow()
        self.profile_name_row.set_title(_("Profile Name"))
        self.profile_name_row.set_text(self.window.config_manager.get('certificates.profile_name', ''))
        self.profile_name_row.connect("changed", self._on_profile_name_changed)
        self.profile_group.add(self.profile_name_row)
        
        # Validation section
        self.validation_group = Adw.PreferencesGroup()
        self.validation_group.set_title(_("Certificate Validation"))
        self.append(self.validation_group)

        # Validate button
        validate_row = Adw.ActionRow()
        validate_row.set_title(_("Validate Certificates"))
        validate_row.set_subtitle(_("Check if certificates are valid and properly configured"))

        self.validate_button = Gtk.Button.new_with_label(_("Validate"))
        self.validate_button.set_valign(Gtk.Align.CENTER)
        self.validate_button.connect("clicked", self._on_validate_certificates)
        validate_row.add_suffix(self.validate_button)

        self.validation_group.add(validate_row)

        # Actions
        self.actions_group = Adw.PreferencesGroup()
        self.append(self.actions_group)

        # Continue button
        continue_row = Adw.ActionRow()
        continue_row.set_title(_("Continue to Installation"))
        continue_row.set_subtitle(_("Start the Jellyfin installation process"))

        self.continue_button = Gtk.Button.new_with_label(_("Continue"))
        self.continue_button.set_valign(Gtk.Align.CENTER)
        self.continue_button.add_css_class("suggested-action")
        self.continue_button.set_sensitive(False)
        self.continue_button.connect("clicked", self._on_continue)
        continue_row.add_suffix(self.continue_button)
        
        self.actions_group.add(continue_row)
        
        # Load existing certificate info
        self._load_certificate_info()
        
    def _browse_file(self, cert_type):
        """Browse for certificate file."""
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title(_("Select {cert_type} certificate").format(cert_type=cert_type))

        # Set file filter for P12 files
        filter_p12 = Gtk.FileFilter()
        filter_p12.set_name(_("P12 Certificate Files"))
        filter_p12.add_pattern("*.p12")
        filter_p12.add_pattern("*.P12")
        
        filter_list = Gio.ListStore()
        filter_list.append(filter_p12)
        file_dialog.set_filters(filter_list)
        
        def on_file_selected(dialog, result):
            try:
                file = dialog.open_finish(result)
                if file:
                    file_path = file.get_path()
                    self._set_certificate_file(cert_type, file_path)
            except Exception as e:
                self.window.logger.error(f"Error selecting certificate file: {e}")
                
        file_dialog.open(self.window, None, on_file_selected)
        
    def _set_certificate_file(self, cert_type, file_path):
        """Set certificate file path."""
        config_key = f'certificates.{cert_type}_cert_path'
        self.window.config_manager.set(config_key, file_path)

        # Update UI
        if cert_type == "author":
            self.author_cert_row.set_subtitle(_("Selected: {path}").format(path=file_path))
            self.author_cert_button.set_label(_("Change"))
        else:
            self.dist_cert_row.set_subtitle(_("Selected: {path}").format(path=file_path))
            self.dist_cert_button.set_label(_("Change"))
            
        self._check_certificate_completeness()
        
    def _on_password_changed(self, entry):
        """Handle password changes."""
        self.window.config_manager.set('certificates.password', entry.get_text())
        self._check_certificate_completeness()
        
    def _on_profile_name_changed(self, entry):
        """Handle profile name changes."""
        self.window.config_manager.set('certificates.profile_name', entry.get_text())
        
    def _load_certificate_info(self):
        """Load existing certificate information."""
        # Load author certificate
        author_path = self.window.config_manager.get('certificates.author_cert_path')
        if author_path:
            self.author_cert_row.set_subtitle(_("Selected: {path}").format(path=author_path))
            self.author_cert_button.set_label(_("Change"))

        # Load distributor certificate
        dist_path = self.window.config_manager.get('certificates.distributor_cert_path')
        if dist_path:
            self.dist_cert_row.set_subtitle(_("Selected: {path}").format(path=dist_path))
            self.dist_cert_button.set_label(_("Change"))
            
        self._check_certificate_completeness()
        
    def _check_certificate_completeness(self):
        """Check if all required certificate info is provided."""
        author_path = self.window.config_manager.get('certificates.author_cert_path')
        dist_path = self.window.config_manager.get('certificates.distributor_cert_path')
        password = self.window.config_manager.get('certificates.password')
        
        is_complete = all([author_path, dist_path, password])
        self.validate_button.set_sensitive(is_complete)
        
    def _on_validate_certificates(self, button):
        """Validate the certificates."""
        button.set_sensitive(False)
        spinner = Gtk.Spinner()
        spinner.start()
        button.get_parent().add_suffix(spinner)
        
        def on_validation_result(success, message):
            button.set_sensitive(True)
            button.get_parent().remove(spinner)

            if success:
                self.continue_button.set_sensitive(True)
                self._show_success(_("Certificates validated successfully!"))
            else:
                self._show_error(_("Certificate validation failed: {message}").format(message=message))
                
        author_path = self.window.config_manager.get('certificates.author_cert_path')
        dist_path = self.window.config_manager.get('certificates.distributor_cert_path')
        password = self.window.config_manager.get('certificates.password')
        
        self.cert_service.validate_certificates_async(
            author_path, dist_path, password, on_validation_result
        )
        
    def _on_continue(self, button):
        """Continue to installation page."""
        self.window.navigate_to_page(self.window.install_page, _("Installation"))
        
    def _show_error(self, message):
        """Show error message."""
        self.window.logger.error(message)
        ErrorNotification.show_toast(self.window, message, timeout=5)

    def _show_success(self, message):
        """Show success message."""
        self.window.logger.info(message)
        ErrorNotification.show_toast(self.window, message, timeout=3)