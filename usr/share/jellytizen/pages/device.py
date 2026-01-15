# pages/device.py
import gi
import socket
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
from services.device import DeviceService
from utils.validators import NetworkValidator
from utils.i18n import _
from utils.ui_helpers import ErrorNotification

class DevicePage(Gtk.ScrolledWindow):
    """Device discovery and connection page with improved UX flow."""

    def __init__(self, window):
        super().__init__()

        self.window = window
        self.device_service = DeviceService(logger=window.logger)
        self.validator = NetworkValidator()
        
        # Keep track of device rows for proper cleanup
        self.device_rows = []
        
        # Configure scrolled window to prevent window resize
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_propagate_natural_height(False)
        self.set_propagate_natural_width(False)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the device page UI with inline developer mode instructions."""
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
        
        # Header
        header_group = Adw.PreferencesGroup()
        header_group.set_title(_("Device Setup"))
        header_group.set_description(_("Connect to your Samsung Tizen TV or projector"))
        main_box.append(header_group)

        # ============================================
        # DEVELOPER MODE INSTRUCTIONS (INLINE - MANDATORY STEP)
        # ============================================
        self.dev_instructions_group = Adw.PreferencesGroup()
        self.dev_instructions_group.set_title(_("⚠️ Required Step: Enable Developer Mode"))
        self.dev_instructions_group.set_description(_("You must complete these steps on your Samsung TV before connecting"))
        main_box.append(self.dev_instructions_group)

        # Step 1
        step1 = Adw.ActionRow()
        step1.set_title(_("1. Open Smart Hub"))
        step1.set_subtitle(_("On the TV, open the 'Smart Hub'"))
        step1_icon = Gtk.Image.new_from_icon_name("tv-symbolic")
        step1.add_prefix(step1_icon)
        self.dev_instructions_group.add(step1)

        # Step 2
        step2 = Adw.ActionRow()
        step2.set_title(_("2. Go to Apps Panel"))
        step2.set_subtitle(_("Select the 'Apps' panel in Smart Hub"))
        step2_icon = Gtk.Image.new_from_icon_name("view-app-grid-symbolic")
        step2.add_prefix(step2_icon)
        self.dev_instructions_group.add(step2)

        # Step 3
        step3 = Adw.ActionRow()
        step3.set_title(_("3. Enter Secret Code"))
        step3.set_subtitle(_("Press '123' button (or long press Home) then type '12345' with on-screen keyboard"))
        step3_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        step3.add_prefix(step3_icon)
        self.dev_instructions_group.add(step3)

        # Step 4
        step4 = Adw.ActionRow()
        step4.set_title(_("4. Toggle Developer Mode"))
        step4.set_subtitle(_("Toggle the 'Developer' button to 'On'"))
        step4_icon = Gtk.Image.new_from_icon_name("preferences-other-symbolic")
        step4.add_prefix(step4_icon)
        self.dev_instructions_group.add(step4)

        # Step 5 - With IP address
        local_ip = self._get_local_ip()
        step5 = Adw.ActionRow()
        step5.set_title(_("5. Enter Host PC IP"))
        step5.set_subtitle(_("Enter your computer's IP address: {ip}").format(ip=local_ip))
        step5_icon = Gtk.Image.new_from_icon_name("network-wired-symbolic")
        step5.add_prefix(step5_icon)
        
        # Copy IP button inline
        copy_button = Gtk.Button.new_with_label(_("Copy IP"))
        copy_button.set_valign(Gtk.Align.CENTER)
        copy_button.add_css_class("suggested-action")
        copy_button.connect("clicked", self._copy_ip_to_clipboard)
        step5.add_suffix(copy_button)
        self.dev_instructions_group.add(step5)

        # Important notes group
        notes_group = Adw.PreferencesGroup()
        notes_group.set_title(_("Important Notes"))
        main_box.append(notes_group)

        # Note about languages
        note1 = Adw.ActionRow()
        note1.set_title(_("Right-to-Left Languages"))
        note1.set_subtitle(_("If TV uses Arabic/Hebrew, enter the IP address backwards"))
        note1_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        note1.add_prefix(note1_icon)
        notes_group.add(note1)

        # Note about network
        note2 = Adw.ActionRow()
        note2.set_title(_("Network Connection"))
        note2.set_subtitle(_("Ensure TV and computer are on the same network"))
        note2_icon = Gtk.Image.new_from_icon_name("network-wireless-symbolic")
        note2.add_prefix(note2_icon)
        notes_group.add(note2)

        # ============================================
        # DEVELOPER MODE CONFIRMATION (MANDATORY)
        # ============================================
        self.confirm_group = Adw.PreferencesGroup()
        self.confirm_group.set_title(_("Confirmation"))
        main_box.append(self.confirm_group)

        # Developer mode confirmation toggle
        self.dev_mode_row = Adw.ActionRow()
        self.dev_mode_row.set_title(_("Developer Mode Enabled"))
        self.dev_mode_row.set_subtitle(_("I confirm I have completed the steps above on my TV"))

        # Developer mode switch
        self.dev_mode_switch = Gtk.Switch()
        self.dev_mode_switch.set_valign(Gtk.Align.CENTER)
        self.dev_mode_switch.set_active(self.window.config_manager.get('device.developer_mode', False))
        self.dev_mode_switch.connect("notify::active", self._on_dev_mode_changed)
        self.dev_mode_row.add_suffix(self.dev_mode_switch)
        
        self.confirm_group.add(self.dev_mode_row)

        # ============================================
        # DISCOVERY SECTION
        # ============================================
        self.discovery_group = Adw.PreferencesGroup()
        self.discovery_group.set_title(_("Device Discovery"))
        main_box.append(self.discovery_group)

        # Scan network row
        self.scan_row = Adw.ActionRow()
        self.scan_row.set_title(_("Scan Network"))
        self.scan_row.set_subtitle(_("Automatically discover Samsung devices on your network"))

        self.scan_button = Gtk.Button.new_with_label(_("Scan"))
        self.scan_button.set_valign(Gtk.Align.CENTER)
        self.scan_button.add_css_class("suggested-action")
        self.scan_button.connect("clicked", self._on_scan_network)
        self.scan_row.add_suffix(self.scan_button)
        
        self.discovery_group.add(self.scan_row)
        
        # Discovered devices list
        self.devices_group = Adw.PreferencesGroup()
        self.devices_group.set_title(_("Discovered Devices"))
        self.devices_group.set_description(_("Select your target device"))
        main_box.append(self.devices_group)

        # ============================================
        # MANUAL CONNECTION SECTION
        # ============================================
        self.manual_group = Adw.PreferencesGroup()
        self.manual_group.set_title(_("Manual Connection"))
        self.manual_group.set_description(_("Enter device details manually"))
        main_box.append(self.manual_group)

        # IP address entry
        self.ip_row = Adw.EntryRow()
        self.ip_row.set_title(_("Device IP Address"))
        self.ip_row.set_text(self.window.config_manager.get('device.ip', ''))
        self.ip_row.connect("changed", self._on_ip_changed)
        self.manual_group.add(self.ip_row)

        # ============================================
        # ACTIONS
        # ============================================
        self.actions_group = Adw.PreferencesGroup()
        main_box.append(self.actions_group)

        # Connect button - DISABLED until developer mode is confirmed
        self.connect_row = Adw.ActionRow()
        self.connect_row.set_title(_("Connect to Device"))
        self.connect_row.set_subtitle(_("Establish connection with your TV"))

        self.connect_button = Gtk.Button.new_with_label(_("Connect"))
        self.connect_button.set_valign(Gtk.Align.CENTER)
        self.connect_button.add_css_class("suggested-action")
        # Initially disabled - only enabled when developer mode is confirmed
        self.connect_button.set_sensitive(self.dev_mode_switch.get_active())
        self.connect_button.connect("clicked", self._on_connect_device)
        self.connect_row.add_suffix(self.connect_button)

        self.actions_group.add(self.connect_row)

        # Continue button (initially disabled)
        self.continue_row = Adw.ActionRow()
        self.continue_row.set_title(_("Continue to Certificates"))
        self.continue_row.set_subtitle(_("Setup developer certificates"))

        self.continue_button = Gtk.Button.new_with_label(_("Continue"))
        self.continue_button.set_valign(Gtk.Align.CENTER)
        self.continue_button.add_css_class("suggested-action")
        self.continue_button.set_sensitive(False)
        self.continue_button.connect("clicked", self._on_continue)
        self.continue_row.add_suffix(self.continue_button)
        
        self.actions_group.add(self.continue_row)

    def _get_local_ip(self):
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return _("Unable to determine IP")

    def _copy_ip_to_clipboard(self, button):
        """Copy IP to clipboard."""
        ip = self._get_local_ip()
        clipboard = self.window.get_clipboard()
        clipboard.set(ip)
        original_label = button.get_label()
        button.set_label(_("Copied!"))
        GLib.timeout_add(2000, lambda: button.set_label(original_label))
        
    def _on_scan_network(self, button):
        """Scan network for Samsung devices."""
        # Disable button and show spinner
        button.set_sensitive(False)
        button.set_label(_("Scanning..."))
        
        # Create and start spinner
        self.scan_spinner = Gtk.Spinner()
        self.scan_spinner.start()
        self.scan_row.add_suffix(self.scan_spinner)
        
        def on_scan_complete(devices):
            # Re-enable button and remove spinner
            button.set_sensitive(True)
            button.set_label(_("Scan"))
            self.scan_row.remove(self.scan_spinner)
            self._update_devices_list(devices)
            
        self.device_service.scan_network_async(on_scan_complete)
        
    def _update_devices_list(self, devices):
        """Update the discovered devices list."""
        # Clear existing device rows properly
        for row in self.device_rows:
            self.devices_group.remove(row)
        self.device_rows.clear()
        
        if not devices:
            no_devices_row = Adw.ActionRow()
            no_devices_row.set_title(_("No devices found"))
            no_devices_row.set_subtitle(_("Try manual connection or check network"))
            self.devices_group.add(no_devices_row)
            self.device_rows.append(no_devices_row)
            return

        for device in devices:
            device_row = Adw.ActionRow()
            device_row.set_title(device.get('name', _('Unknown Device')))
            device_row.set_subtitle(_("IP: {ip} | Model: {model}").format(ip=device['ip'], model=device.get('model', _('Unknown'))))

            select_button = Gtk.Button.new_with_label(_("Select"))
            select_button.set_valign(Gtk.Align.CENTER)
            select_button.connect("clicked", lambda b, ip=device['ip']: self._select_device(ip))
            device_row.add_suffix(select_button)
            
            self.devices_group.add(device_row)
            self.device_rows.append(device_row)
            
        # Update devices group description with count
        device_count = len(devices)
        if device_count == 1:
            self.devices_group.set_description(_("Found 1 device - Select your target device"))
        else:
            self.devices_group.set_description(_("Found {count} devices - Select your target device").format(count=device_count))
            
    def _select_device(self, ip):
        """Select a discovered device."""
        self.ip_row.set_text(ip)
        self.window.config_manager.set('device.ip', ip)
        self.window.logger.info(f"Selected device: {ip}")
        self._show_success(_("Device selected: {ip}").format(ip=ip))
        
    def _on_ip_changed(self, entry):
        """Handle IP address changes."""
        ip = entry.get_text()
        self.window.config_manager.set('device.ip', ip)
        
        # Validate IP
        is_valid = self.validator.is_valid_ip(ip)
        if ip and not is_valid:
            entry.add_css_class("error")
        else:
            entry.remove_css_class("error")
            
    def _on_dev_mode_changed(self, switch, param):
        """Handle developer mode toggle - enables/disables connect button."""
        is_active = switch.get_active()
        self.window.config_manager.set('device.developer_mode', is_active)
        # Enable connect button only when developer mode is confirmed
        self.connect_button.set_sensitive(is_active)
        
    def _on_connect_device(self, button):
        """Connect to the device."""
        ip = self.ip_row.get_text().strip()

        if not ip:
            self._show_error(_("Please enter a device IP address"))
            return

        if not self.validator.is_valid_ip(ip):
            self._show_error(_("Please enter a valid IP address"))
            return

        # Disable button and show spinner
        button.set_sensitive(False)
        button.set_label(_("Connecting..."))
        
        self.connect_spinner = Gtk.Spinner()
        self.connect_spinner.start()
        self.connect_row.add_suffix(self.connect_spinner)
        
        def on_connection_result(success, message):
            # Re-enable button and remove spinner
            button.set_sensitive(True)
            button.set_label(_("Connect"))
            self.connect_row.remove(self.connect_spinner)

            if success:
                self.continue_button.set_sensitive(True)
                self._show_success(_("Connected successfully!"))
            else:
                self._show_error(_("Connection failed: {message}").format(message=message))
                
        dev_mode = self.dev_mode_switch.get_active()
        self.device_service.connect_device_async(ip, dev_mode, on_connection_result)
        
    def _on_continue(self, button):
        """Continue to certificates page."""
        self.window.navigate_to_page(self.window.certificates_page, _("Certificates"))
        
    def _show_error(self, message):
        """Show error toast."""
        self.window.logger.error(message)
        ErrorNotification.show_toast(self.window, message, timeout=5)

    def _show_success(self, message):
        """Show success toast."""
        self.window.logger.info(message)
        ErrorNotification.show_toast(self.window, message, timeout=3)