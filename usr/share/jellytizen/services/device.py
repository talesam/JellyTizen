# services/device.py
from __future__ import annotations

import subprocess
import threading
import socket
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, List, Dict, Any

from gi.repository import GLib
from utils.logger import Logger
from utils.constants import *
from utils.exceptions import (
    DeviceError,
    DeviceNotFoundError,
    DeviceConnectionError,
    DeviceNotReachableError,
    SDBError,
    NetworkError,
    NetworkScanError,
    NetworkTimeoutError
)
from utils.validators import NetworkValidator


class DeviceService:
    """Service for device discovery and connection."""

    def __init__(self, logger: Optional[Logger] = None) -> None:
        """
        Initialize Device service.

        Args:
            logger: Logger instance. Creates new one if not provided.
        """
        self.logger: Logger = logger or Logger()
        self.connected_device: Optional[str] = None
        self.scan_timeout: int = TIMEOUT_NETWORK_SCAN

    def scan_network_async(self, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Scan network for Samsung devices asynchronously."""
        def scan_network():
            try:
                self.logger.info("Starting Samsung TV scan")
                devices = []

                # Get local IP using the method that worked in tests
                local_ip = self._get_local_ip()
                if not local_ip:
                    self.logger.error("Could not determine local IP address")
                    GLib.idle_add(callback, [])
                    return

                self.logger.info(f"Local IP: {local_ip}")
                network_base = '.'.join(local_ip.split('.')[:-1])
                self.logger.info(f"Scanning network: {network_base}.{NETWORK_IP_RANGE_START}-{NETWORK_IP_RANGE_END}")

                # Use threading like in the successful test
                devices = self._scan_ip_range_threaded(network_base)

                self.logger.info(f"Scan completed. Found {len(devices)} Samsung devices")
                GLib.idle_add(callback, devices)

            except NetworkScanError as e:
                self.logger.error(f"Network scan failed: {e}")
                GLib.idle_add(callback, [])
            except Exception as e:
                self.logger.exception(f"Unexpected error during network scan: {e}")
                GLib.idle_add(callback, [])

        thread = threading.Thread(target=scan_network, daemon=True)
        thread.start()

    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address using the method that worked."""
        try:
            # This method worked in the test
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(TIMEOUT_SOCKET)
            s.connect((NETWORK_DNS_SERVER, NETWORK_DNS_PORT))
            local_ip = s.getsockname()[0]
            s.close()
            self.logger.debug(f"Local IP detected: {local_ip}")
            return local_ip
        except socket.timeout:
            self.logger.warning("Socket timeout getting local IP")
            return None
        except socket.error as e:
            self.logger.warning(f"Socket error getting local IP: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error getting local IP: {e}")
            return None

    def _scan_ip_range_threaded(self, network_base: str) -> List[Dict[str, Any]]:
        """Scan IP range with threading - based on successful test."""
        devices = []

        def check_single_ip(ip_suffix):
            ip = f"{network_base}.{ip_suffix}"
            return self._check_samsung_device_fast(ip)

        # Use configured number of workers
        self.logger.debug(f"Starting threaded scan with {SCAN_MAX_WORKERS} workers")

        with ThreadPoolExecutor(max_workers=SCAN_MAX_WORKERS) as executor:
            futures = [
                executor.submit(check_single_ip, i)
                for i in range(NETWORK_IP_RANGE_START, NETWORK_IP_RANGE_END + 1)
            ]

            try:
                for future in as_completed(futures, timeout=self.scan_timeout):
                    try:
                        result = future.result()
                        if result:
                            devices.append(result)
                            self.logger.info(f"Found Samsung device: {result['ip']}")
                    except Exception as e:
                        self.logger.debug(f"Future result error: {e}")

            except TimeoutError:
                self.logger.warning(f"Scan timeout after {self.scan_timeout} seconds")
            except Exception as e:
                self.logger.exception(f"Error during threaded scan: {e}")

        return devices

    def _check_samsung_device_fast(self, ip: str) -> Optional[Dict[str, Any]]:
        """Fast check if IP is Samsung device - using methods that worked."""
        # Quick ping test first (this worked in tests)
        if not self._ping_quick(ip):
            return None

        # Check port 8001 - the one that worked in the test
        if self._check_port_quick(ip, SAMSUNG_API_PORT):
            # Try the Samsung identification that worked
            samsung_info = self._identify_samsung_device(ip, SAMSUNG_API_PORT)
            if samsung_info:
                return {
                    'ip': ip,
                    'port': SAMSUNG_API_PORT,
                    'name': samsung_info.get('name', f'Samsung TV ({ip})'),
                    'model': samsung_info.get('model', 'Unknown Model')
                }

        return None

    def _ping_quick(self, ip: str) -> bool:
        """Quick ping test - system ping worked in tests."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', ip],
                capture_output=True,
                timeout=TIMEOUT_PING
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.logger.debug(f"Ping timeout for {ip}")
            return False
        except FileNotFoundError:
            self.logger.warning("Ping command not found")
            return False
        except Exception as e:
            self.logger.debug(f"Ping error for {ip}: {e}")
            return False

    def _check_port_quick(self, ip: str, port: int) -> bool:
        """Quick port check - socket connect worked in tests."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT_SOCKET)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except socket.timeout:
            return False
        except socket.error:
            return False
        except Exception as e:
            self.logger.debug(f"Port check error for {ip}:{port}: {e}")
            return False

    def _identify_samsung_device(self, ip: str, port: int) -> Optional[Dict[str, str]]:
        """Identify Samsung device using endpoint that worked."""
        # The endpoint that worked in the test
        endpoint = f"http://{ip}:{port}{SAMSUNG_API_ENDPOINT}"

        try:
            req = urllib.request.Request(endpoint)
            req.add_header('User-Agent', f'{APP_NAME}/{APP_VERSION}')

            with urllib.request.urlopen(req, timeout=TIMEOUT_HTTP_REQUEST) as response:
                if response.status == 200:
                    content = response.read().decode('utf-8', errors='ignore')

                    # Check for Samsung indicators (these were found in tests)
                    found_indicators = [
                        ind for ind in SAMSUNG_DEVICE_INDICATORS
                        if ind.lower() in content.lower()
                    ]

                    if found_indicators:
                        # Try to parse device info from JSON
                        try:
                            data = json.loads(content)
                            device_info = data.get('device', {})
                            return {
                                'name': device_info.get('name', 'Samsung TV'),
                                'model': device_info.get('modelName', 'Unknown Model'),
                                'os': device_info.get('OS', 'Tizen'),
                                'language': device_info.get('Language', 'Unknown')
                            }
                        except json.JSONDecodeError:
                            # Still Samsung, just couldn't parse JSON
                            self.logger.debug(f"Could not parse JSON from {ip}")
                            return {
                                'name': 'Samsung TV',
                                'model': 'Unknown Model'
                            }

        except urllib.error.URLError as e:
            self.logger.debug(f"URL error identifying Samsung device at {ip}: {e}")
        except socket.timeout:
            self.logger.debug(f"Timeout identifying Samsung device at {ip}")
        except Exception as e:
            self.logger.debug(f"Error identifying Samsung device at {ip}: {e}")

        return None

    def connect_device_async(
        self,
        ip: str,
        developer_mode: bool,
        callback: Callable[[bool, str], None]
    ) -> None:
        """Connect to device asynchronously."""
        def connect():
            try:
                # Validate IP address first
                if not NetworkValidator.is_valid_ip(ip):
                    self.logger.error(f"Invalid IP address format: {ip}")
                    GLib.idle_add(callback, False, "Invalid IP address format")
                    return

                self.logger.info(f"Connecting to {ip} (dev mode: {developer_mode})")

                # First verify the device is still reachable
                if not self._check_port_quick(ip, SAMSUNG_API_PORT):
                    error_msg = f"Device not reachable on port {SAMSUNG_API_PORT}"
                    self.logger.warning(error_msg)
                    GLib.idle_add(callback, False, error_msg)
                    return

                if developer_mode:
                    success = self._connect_developer_mode(ip)
                else:
                    success = self._connect_normal_mode(ip)

                if success:
                    self.connected_device = ip
                    self.logger.info(f"Successfully connected to {ip}")
                    GLib.idle_add(callback, True, "Connected successfully")
                else:
                    self.logger.error(f"Failed to establish connection to {ip}")
                    GLib.idle_add(callback, False, "Failed to establish connection")

            except DeviceConnectionError as e:
                self.logger.error(f"Device connection error: {e}")
                GLib.idle_add(callback, False, str(e))
            except Exception as e:
                self.logger.exception(f"Unexpected connection error: {e}")
                GLib.idle_add(callback, False, str(e))

        thread = threading.Thread(target=connect, daemon=True)
        thread.start()

    def _connect_developer_mode(self, ip: str) -> bool:
        """Connect to device in developer mode using SDB."""
        try:
            # Check if sdb is available
            result = subprocess.run(
                ['which', 'sdb'],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SOCKET
            )

            if result.returncode != 0:
                self.logger.error("SDB (Samsung Debug Bridge) not found")
                return False

            self.logger.info(f"Attempting SDB connection to {ip}:{SDB_PORT}")

            # Try to connect via SDB
            result = subprocess.run(
                ['sdb', 'connect', f"{ip}:{SDB_PORT}"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SDB_CONNECT
            )

            if result.returncode == 0:
                # Verify connection
                result = subprocess.run(
                    ['sdb', 'devices'],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SDB_DEVICES
                )

                is_connected = ip in result.stdout
                self.logger.info(f"SDB connection result: {is_connected}")
                return is_connected

            self.logger.warning(f"SDB connect failed: {result.stderr}")
            return False

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"SDB operation timed out: {e}")
            return False
        except FileNotFoundError:
            self.logger.error("SDB executable not found")
            return False
        except Exception as e:
            self.logger.exception(f"Developer mode connection error: {e}")
            return False

    def _connect_normal_mode(self, ip: str) -> bool:
        """Connect to device in normal mode."""
        try:
            # For normal mode, verify we can reach the Samsung API
            samsung_info = self._identify_samsung_device(ip, SAMSUNG_API_PORT)

            if samsung_info:
                self.logger.info(f"Normal mode connection successful - detected {samsung_info['name']}")
                return True
            else:
                self.logger.warning("Normal mode connection failed - could not verify Samsung device")
                return False

        except Exception as e:
            self.logger.exception(f"Normal mode connection error: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to a device."""
        return self.connected_device is not None

    def disconnect(self) -> None:
        """Disconnect from current device."""
        if self.connected_device:
            try:
                self.logger.info(f"Disconnecting from {self.connected_device}")
                subprocess.run(
                    ['sdb', 'disconnect', self.connected_device],
                    capture_output=True,
                    timeout=TIMEOUT_SDB_DISCONNECT
                )
                self.logger.info(f"Disconnected from {self.connected_device}")
            except subprocess.TimeoutExpired:
                self.logger.warning("SDB disconnect timed out")
            except FileNotFoundError:
                self.logger.warning("SDB executable not found for disconnect")
            except Exception as e:
                self.logger.warning(f"Disconnect error: {e}")

        self.connected_device = None
