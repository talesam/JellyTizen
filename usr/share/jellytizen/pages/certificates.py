# pages/certificates.py
import gi
import webbrowser
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio
from services.certificates import CertificateService
from utils.i18n import _
from utils.ui_helpers import ErrorNotification

class CertificatesPage(Gtk.ScrolledWindow):
    """Certificate management page with improved UX and explanations."""

    def __init__(self, window):
        super().__init__()

        self.window = window
        self.cert_service = CertificateService(logger=window.logger)
        
        # Configure scrolled window
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_propagate_natural_height(False)
        self.set_propagate_natural_width(False)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the certificates page UI with clear explanations."""
        # Use clamp for better layout
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        self.set_child(clamp)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(main_box)

        # ============================================
        # HEADER WITH EXPLANATION
        # ============================================
        header_group = Adw.PreferencesGroup()
        header_group.set_title(_("Developer Certificates"))
        header_group.set_description(_("Certificates are required to install apps on Samsung TVs"))
        main_box.append(header_group)

        # ============================================
        # WHAT ARE CERTIFICATES - EXPLANATION
        # ============================================
        explanation_group = Adw.PreferencesGroup()
        explanation_group.set_title(_("📋 What are Developer Certificates?"))
        explanation_group.set_description(_("Samsung requires signed apps. You need certificates from Tizen Studio."))
        main_box.append(explanation_group)

        # Explanation row 1
        exp1 = Adw.ActionRow()
        exp1.set_title(_("Author Certificate (author.p12)"))
        exp1.set_subtitle(_("Your personal certificate that identifies you as the app developer"))
        exp1_icon = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
        exp1.add_prefix(exp1_icon)
        explanation_group.add(exp1)

        # Explanation row 2
        exp2 = Adw.ActionRow()
        exp2.set_title(_("Distributor Certificate (distributor.p12)"))
        exp2.set_subtitle(_("Samsung's certificate that allows app installation on devices"))
        exp2_icon = Gtk.Image.new_from_icon_name("emblem-documents-symbolic")
        exp2.add_prefix(exp2_icon)
        explanation_group.add(exp2)

        # ============================================
        # HOW TO GET CERTIFICATES
        # ============================================
        howto_group = Adw.PreferencesGroup()
        howto_group.set_title(_("🔧 How to Get Certificates"))
        howto_group.set_description(_("Follow these steps to create your certificates"))
        main_box.append(howto_group)

        # Step 1
        step1 = Adw.ActionRow()
        step1.set_title(_("1. Install Tizen Studio"))
        step1.set_subtitle(_("Download from Samsung Developer website"))
        step1_icon = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        step1.add_prefix(step1_icon)
        
        download_btn = Gtk.Button.new_with_label(_("Download"))
        download_btn.set_valign(Gtk.Align.CENTER)
        download_btn.add_css_class("suggested-action")
        download_btn.connect("clicked", lambda b: webbrowser.open("https://developer.samsung.com/tizen"))
        step1.add_suffix(download_btn)
        howto_group.add(step1)

        # Step 2
        step2 = Adw.ActionRow()
        step2.set_title(_("2. Open Certificate Manager"))
        step2.set_subtitle(_("In Tizen Studio: Tools → Certificate Manager"))
        step2_icon = Gtk.Image.new_from_icon_name("application-certificate-symbolic")
        step2.add_prefix(step2_icon)
        howto_group.add(step2)

        # Step 3
        step3 = Adw.ActionRow()
        step3.set_title(_("3. Create Samsung Certificate"))
        step3.set_subtitle(_("Click '+' → Samsung Certificate → TV → Create new profile"))
        step3_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        step3.add_prefix(step3_icon)
        howto_group.add(step3)

        # Step 4
        step4 = Adw.ActionRow()
        step4.set_title(_("4. Sign in with Samsung Account"))
        step4.set_subtitle(_("Use the same account registered on your TV"))
        step4_icon = Gtk.Image.new_from_icon_name("system-users-symbolic")
        step4.add_prefix(step4_icon)
        howto_group.add(step4)

        # Step 5
        step5 = Adw.ActionRow()
        step5.set_title(_("5. Add Your TV's DUID"))
        step5.set_subtitle(_("The DUID is shown in the TV's Developer Mode settings"))
        step5_icon = Gtk.Image.new_from_icon_name("tv-symbolic")
        step5.add_prefix(step5_icon)
        howto_group.add(step5)

        # Step 6
        step6 = Adw.ActionRow()
        step6.set_title(_("6. Export Certificates"))
        step6.set_subtitle(_("Certificates are saved in ~/SamsungCertificate/<profile_name>/"))
        step6_icon = Gtk.Image.new_from_icon_name("folder-symbolic")
        step6.add_prefix(step6_icon)
        howto_group.add(step6)

        # ============================================
        # UPLOAD CERTIFICATES SECTION
        # ============================================
        self.files_group = Adw.PreferencesGroup()
        self.files_group.set_title(_("📁 Upload Your Certificates"))
        self.files_group.set_description(_("Select the .p12 certificate files from your computer"))
        main_box.append(self.files_group)

        # Author certificate
        self.author_cert_row = Adw.ActionRow()
        self.author_cert_row.set_title(_("Author Certificate"))
        self.author_cert_row.set_subtitle(_("Select author.p12 file"))
        author_icon = Gtk.Image.new_from_icon_name("contact-new-symbolic")
        self.author_cert_row.add_prefix(author_icon)

        self.author_cert_button = Gtk.Button.new_with_label(_("Browse"))
        self.author_cert_button.set_valign(Gtk.Align.CENTER)
        self.author_cert_button.connect("clicked", lambda b: self._browse_file("author"))
        self.author_cert_row.add_suffix(self.author_cert_button)
        
        self.files_group.add(self.author_cert_row)
        
        # Distributor certificate
        self.dist_cert_row = Adw.ActionRow()
        self.dist_cert_row.set_title(_("Distributor Certificate"))
        self.dist_cert_row.set_subtitle(_("Select distributor.p12 file"))
        dist_icon = Gtk.Image.new_from_icon_name("emblem-documents-symbolic")
        self.dist_cert_row.add_prefix(dist_icon)

        self.dist_cert_button = Gtk.Button.new_with_label(_("Browse"))
        self.dist_cert_button.set_valign(Gtk.Align.CENTER)
        self.dist_cert_button.connect("clicked", lambda b: self._browse_file("distributor"))
        self.dist_cert_row.add_suffix(self.dist_cert_button)

        self.files_group.add(self.dist_cert_row)

        # ============================================
        # PASSWORD SECTION
        # ============================================
        self.password_group = Adw.PreferencesGroup()
        self.password_group.set_title(_("🔐 Certificate Password"))
        self.password_group.set_description(_("Enter the password you chose when creating the certificates"))
        main_box.append(self.password_group)

        # Password entry
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title(_("Password"))
        self.password_row.set_text(self.window.config_manager.get('certificates.password', ''))
        self.password_row.connect("changed", self._on_password_changed)
        self.password_group.add(self.password_row)

        # ============================================
        # PROFILE NAME SECTION
        # ============================================
        self.profile_group = Adw.PreferencesGroup()
        self.profile_group.set_title(_("👤 Developer Profile"))
        self.profile_group.set_description(_("A name to identify this certificate configuration"))
        main_box.append(self.profile_group)

        # Profile name
        self.profile_name_row = Adw.EntryRow()
        self.profile_name_row.set_title(_("Profile Name"))
        saved_profile = self.window.config_manager.get('certificates.profile_name', '')
        self.profile_name_row.set_text(saved_profile if saved_profile else "JellyTizen")
        self.profile_name_row.connect("changed", self._on_profile_name_changed)
        self.profile_group.add(self.profile_name_row)

        # ============================================
        # VALIDATION AND ACTIONS
        # ============================================
        self.actions_group = Adw.PreferencesGroup()
        self.actions_group.set_title(_("✅ Validate and Continue"))
        main_box.append(self.actions_group)

        # Validate button
        self.validate_row = Adw.ActionRow()
        self.validate_row.set_title(_("Validate Certificates"))
        self.validate_row.set_subtitle(_("Check if certificates are valid before continuing"))

        self.validate_button = Gtk.Button.new_with_label(_("Validate"))
        self.validate_button.set_valign(Gtk.Align.CENTER)
        self.validate_button.connect("clicked", self._on_validate_certificates)
        self.validate_row.add_suffix(self.validate_button)

        self.actions_group.add(self.validate_row)

        # Continue button
        self.continue_row = Adw.ActionRow()
        self.continue_row.set_title(_("Continue to Installation"))
        self.continue_row.set_subtitle(_("Proceed to install Jellyfin on your TV"))

        self.continue_button = Gtk.Button.new_with_label(_("Continue"))
        self.continue_button.set_valign(Gtk.Align.CENTER)
        self.continue_button.add_css_class("suggested-action")
        self.continue_button.set_sensitive(False)
        self.continue_button.connect("clicked", self._on_continue)
        self.continue_row.add_suffix(self.continue_button)
        
        self.actions_group.add(self.continue_row)
        
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

        # Get just the filename for display
        filename = file_path.split('/')[-1]

        # Update UI with checkmark
        if cert_type == "author":
            self.author_cert_row.set_subtitle(_("✅ Selected: {filename}").format(filename=filename))
            self.author_cert_button.set_label(_("Change"))
        else:
            self.dist_cert_row.set_subtitle(_("✅ Selected: {filename}").format(filename=filename))
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
            filename = author_path.split('/')[-1]
            self.author_cert_row.set_subtitle(_("✅ Selected: {filename}").format(filename=filename))
            self.author_cert_button.set_label(_("Change"))

        # Load distributor certificate
        dist_path = self.window.config_manager.get('certificates.distributor_cert_path')
        if dist_path:
            filename = dist_path.split('/')[-1]
            self.dist_cert_row.set_subtitle(_("✅ Selected: {filename}").format(filename=filename))
            self.dist_cert_button.set_label(_("Change"))
            
        self._check_certificate_completeness()
        
    def _check_certificate_completeness(self):
        """Check if all required certificate info is provided."""
        author_path = self.window.config_manager.get('certificates.author_cert_path')
        dist_path = self.window.config_manager.get('certificates.distributor_cert_path')
        password = self.window.config_manager.get('certificates.password')
        
        is_complete = all([author_path, dist_path, password])
        self.validate_button.set_sensitive(is_complete)
        
        # Update validate row subtitle based on completeness
        if is_complete:
            self.validate_row.set_subtitle(_("All fields filled - click to validate"))
        else:
            missing = []
            if not author_path:
                missing.append(_("author certificate"))
            if not dist_path:
                missing.append(_("distributor certificate"))
            if not password:
                missing.append(_("password"))
            self.validate_row.set_subtitle(_("Missing: {items}").format(items=", ".join(missing)))
        
    def _on_validate_certificates(self, button):
        """Validate the certificates."""
        button.set_sensitive(False)
        spinner = Gtk.Spinner()
        spinner.start()
        self.validate_row.add_suffix(spinner)
        
        def on_validation_result(success, message):
            button.set_sensitive(True)
            self.validate_row.remove(spinner)

            if success:
                self.continue_button.set_sensitive(True)
                self.validate_row.set_subtitle(_("✅ Certificates are valid!"))
                self._show_success(_("Certificates validated successfully!"))
            else:
                self.validate_row.set_subtitle(_("❌ Validation failed: {message}").format(message=message))
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