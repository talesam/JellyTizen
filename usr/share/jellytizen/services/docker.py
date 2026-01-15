# services/docker.py
from __future__ import annotations

import subprocess
import threading
import os
import shutil
import tempfile
from typing import Callable, Optional, List

from gi.repository import GLib
from utils.logger import Logger
from utils.constants import *
from utils.exceptions import (
    DockerError,
    DockerNotInstalledError,
    DockerNotRunningError,
    DockerImageError,
    DockerContainerError,
    DockerCommandError,
    SDKInstallationError,
    AppBuildError,
    AppInstallError
)


class DockerService:
    """Service for Docker operations and Tizen SDK management."""

    def __init__(self, logger: Optional[Logger] = None) -> None:
        """
        Initialize Docker service.

        Args:
            logger: Logger instance. Creates new one if not provided.
        """
        self.logger: Logger = logger or Logger()
        self.container_name: str = DOCKER_CONTAINER_NAME
        self.image_name: str = DOCKER_IMAGE_NAME
        self.image_tag: str = DOCKER_IMAGE_TAG
        self.workspace_host: str = DOCKER_WORKSPACE_HOST
        self.workspace_container: str = DOCKER_WORKSPACE_CONTAINER

    def is_docker_installed(self) -> bool:
        """Check if Docker is installed."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_DOCKER_VERSION
            )
            is_installed = result.returncode == 0
            if is_installed:
                self.logger.info("Docker is installed")
            else:
                self.logger.warning("Docker is not installed")
            return is_installed
        except subprocess.TimeoutExpired:
            self.logger.error("Docker version check timed out")
            return False
        except FileNotFoundError:
            self.logger.error("Docker executable not found")
            return False
        except Exception as e:
            self.logger.exception(f"Unexpected error checking Docker installation: {e}")
            return False

    def is_docker_running(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_DOCKER_INFO
            )
            is_running = result.returncode == 0
            if is_running:
                self.logger.info("Docker daemon is running")
            else:
                self.logger.warning("Docker daemon is not running")
            return is_running
        except subprocess.TimeoutExpired:
            self.logger.error("Docker info check timed out")
            return False
        except FileNotFoundError:
            self.logger.error("Docker executable not found")
            return False
        except Exception as e:
            self.logger.exception(f"Unexpected error checking Docker status: {e}")
            return False

    def start_docker_async(self, callback: Callable[[bool], None]) -> None:
        """Start Docker service asynchronously."""
        def start_docker():
            try:
                self.logger.info("Attempting to start Docker service")

                for cmd in DOCKER_START_COMMANDS:
                    try:
                        self.logger.debug(f"Trying command: {' '.join(cmd)}")
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=TIMEOUT_DOCKER_START
                        )

                        if result.returncode == 0:
                            self.logger.info(f"Docker start command succeeded: {' '.join(cmd)}")
                            # Wait for Docker to fully start
                            import time
                            time.sleep(3)

                            # Verify Docker is running
                            if self.is_docker_running():
                                self.logger.info("Docker started successfully")
                                GLib.idle_add(callback, True)
                                return
                        else:
                            self.logger.warning(f"Command failed: {result.stderr}")

                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Command timed out: {' '.join(cmd)}")
                        continue
                    except FileNotFoundError:
                        self.logger.debug(f"Command not found: {' '.join(cmd)}")
                        continue

                self.logger.error("All Docker start attempts failed")
                GLib.idle_add(callback, False)

            except Exception as e:
                self.logger.exception(f"Unexpected error starting Docker: {e}")
                GLib.idle_add(callback, False)

        thread = threading.Thread(target=start_docker, daemon=True)
        thread.start()

    def install_docker(self, distro: str) -> None:
        """Install Docker for specific distribution."""
        if distro not in DOCKER_INSTALL_COMMANDS:
            raise DockerError(f"Unsupported distribution: {distro}")

        self.logger.info(f"Installing Docker for {distro}")

        for cmd_list in DOCKER_INSTALL_COMMANDS[distro]:
            try:
                self.logger.info(f"Executing: {' '.join(cmd_list)}")
                result = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_INSTALL
                )

                if result.returncode != 0:
                    self.logger.error(f"Command failed: {result.stderr}")
                    raise DockerError(
                        f"Failed to execute: {' '.join(cmd_list)}",
                        details={'stderr': result.stderr}
                    )

                self.logger.info(f"Command succeeded: {' '.join(cmd_list)}")

            except subprocess.TimeoutExpired as e:
                self.logger.error(f"Command timed out: {' '.join(cmd_list)}")
                raise DockerError(f"Installation command timed out: {' '.join(cmd_list)}")
            except FileNotFoundError:
                self.logger.error(f"Command not found: {cmd_list[0]}")
                raise DockerError(f"Command not found: {cmd_list[0]}")

        self.logger.info("Docker installation completed successfully")

    def prepare_environment_async(self, callback: Callable[[bool, str], None]) -> None:
        """Prepare Docker environment for Tizen development."""
        def prepare():
            try:
                self.logger.info(f"Pulling Tizen builder image: {self.image_name}:{self.image_tag}")

                # Pull the Tizen builder image
                result = subprocess.run(
                    ['docker', 'pull', f"{self.image_name}:{self.image_tag}"],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_PULL
                )

                if result.returncode != 0:
                    error_msg = f"Failed to pull Tizen builder image: {result.stderr}"
                    self.logger.error(error_msg)
                    GLib.idle_add(callback, False, error_msg)
                    return

                self.logger.info("Docker image pulled successfully")

                # Create container if it doesn't exist
                try:
                    subprocess.run(
                        ['docker', 'inspect', self.container_name],
                        capture_output=True,
                        check=True,
                        timeout=TIMEOUT_DOCKER_INFO
                    )
                    self.logger.info(f"Container {self.container_name} already exists")
                except subprocess.CalledProcessError:
                    # Container doesn't exist, create it
                    self.logger.info(f"Creating container: {self.container_name}")
                    result = subprocess.run(
                        [
                            'docker', 'create', '--name', self.container_name,
                            '-v', f"{self.workspace_host}:{self.workspace_container}",
                            f"{self.image_name}:{self.image_tag}"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_DOCKER_EXEC_SHORT
                    )

                    if result.returncode != 0:
                        error_msg = f"Failed to create container: {result.stderr}"
                        self.logger.error(error_msg)
                        GLib.idle_add(callback, False, error_msg)
                        return

                    self.logger.info("Container created successfully")

                GLib.idle_add(callback, True, "Environment ready")

            except subprocess.TimeoutExpired as e:
                error_msg = f"Docker operation timed out: {e}"
                self.logger.error(error_msg)
                GLib.idle_add(callback, False, error_msg)
            except Exception as e:
                self.logger.exception(f"Error preparing environment: {e}")
                GLib.idle_add(callback, False, str(e))

        thread = threading.Thread(target=prepare, daemon=True)
        thread.start()

    def setup_tizen_sdk_async(self, callback: Callable[[bool, str], None]) -> None:
        """Setup Tizen SDK in Docker container."""
        def setup_sdk():
            try:
                self.logger.info("Starting Tizen SDK setup")

                # Start container
                subprocess.run(
                    ['docker', 'start', self.container_name],
                    check=True,
                    timeout=TIMEOUT_DOCKER_START
                )
                self.logger.info("Container started")

                # Download and setup Tizen SDK
                setup_script = f"""
                cd {self.workspace_container}
                if [ ! -d "{TIZEN_SDK_DIR}" ]; then
                    wget -O {TIZEN_SDK_BIN_NAME} {TIZEN_SDK_URL}
                    chmod +x {TIZEN_SDK_BIN_NAME}
                    ./{TIZEN_SDK_BIN_NAME} --accept-license
                fi
                """

                self.logger.debug(f"Executing SDK setup script")
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'bash', '-c', setup_script],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_SDK_SETUP
                )

                if result.returncode == 0:
                    self.logger.info("Tizen SDK setup completed successfully")
                    GLib.idle_add(callback, True, "Tizen SDK ready")
                else:
                    error_msg = f"SDK setup failed: {result.stderr}"
                    self.logger.error(error_msg)
                    GLib.idle_add(callback, False, error_msg)

            except subprocess.TimeoutExpired as e:
                error_msg = f"SDK setup timed out: {e}"
                self.logger.error(error_msg)
                GLib.idle_add(callback, False, error_msg)
            except Exception as e:
                self.logger.exception(f"Error setting up Tizen SDK: {e}")
                GLib.idle_add(callback, False, str(e))

        thread = threading.Thread(target=setup_sdk, daemon=True)
        thread.start()

    def setup_certificates_async(
        self,
        author_cert: str,
        dist_cert: str,
        password: str,
        callback: Callable[[bool, str], None]
    ) -> None:
        """Setup certificates in Docker environment."""
        def setup_certs():
            password_file = None
            try:
                self.logger.info("Setting up certificates")

                # Create workspace directory
                os.makedirs(self.workspace_host, exist_ok=True)

                # Copy certificates to workspace
                shutil.copy2(author_cert, f"{self.workspace_host}/{CERT_AUTHOR_FILENAME}")
                shutil.copy2(dist_cert, f"{self.workspace_host}/{CERT_DISTRIBUTOR_FILENAME}")
                self.logger.info("Certificates copied to workspace")

                # Create temporary password file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                    password_file = f.name
                    f.write(password)

                # Copy password file to workspace
                shutil.copy2(password_file, f"{self.workspace_host}/{CERT_PASSWORD_FILE}")
                self.logger.debug("Password file created securely")

                # Create certificate profile
                cert_script = f"""
                cd {self.workspace_container}
                PASSWORD=$(cat {CERT_PASSWORD_FILE})
                {TIZEN_TOOLS_PATH} security-profiles add -n {DEFAULT_PROFILE_NAME} -a {CERT_AUTHOR_FILENAME} -p "$PASSWORD"
                {TIZEN_TOOLS_PATH} package -t tpk -s {DEFAULT_PROFILE_NAME}
                rm -f {CERT_PASSWORD_FILE}
                """

                self.logger.debug("Executing certificate setup script")
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'bash', '-c', cert_script],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_EXEC_SHORT
                )

                if result.returncode == 0:
                    self.logger.info("Certificates configured successfully")
                    GLib.idle_add(callback, True, "Certificates configured")
                else:
                    error_msg = f"Certificate setup failed: {result.stderr}"
                    self.logger.error(error_msg)
                    GLib.idle_add(callback, False, error_msg)

            except Exception as e:
                self.logger.exception(f"Error setting up certificates: {e}")
                GLib.idle_add(callback, False, str(e))
            finally:
                # Clean up temporary password file
                if password_file and os.path.exists(password_file):
                    try:
                        os.unlink(password_file)
                        self.logger.debug("Temporary password file removed")
                    except OSError as e:
                        self.logger.warning(f"Failed to remove password file: {e}")

        thread = threading.Thread(target=setup_certs, daemon=True)
        thread.start()

    def build_jellyfin_app_async(self, callback: Callable[[bool, str], None]) -> None:
        """Build the Jellyfin application."""
        def build_app():
            try:
                self.logger.info("Starting Jellyfin app build")

                build_script = f"""
                cd {self.workspace_container}
                if [ ! -d "{JELLYFIN_REPO_DIR}" ]; then
                    git clone {JELLYFIN_REPO_URL}
                fi
                cd {JELLYFIN_REPO_DIR}
                {TIZEN_TOOLS_PATH} build-web
                {TIZEN_TOOLS_PATH} package -t wgt -s {DEFAULT_PROFILE_NAME}
                """

                self.logger.debug("Executing build script")
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'bash', '-c', build_script],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_EXEC_LONG
                )

                if result.returncode == 0:
                    self.logger.info("Application built successfully")
                    GLib.idle_add(callback, True, "Application built successfully")
                else:
                    error_msg = f"Build failed: {result.stderr}"
                    self.logger.error(error_msg)
                    GLib.idle_add(callback, False, error_msg)

            except subprocess.TimeoutExpired as e:
                error_msg = f"Build timed out: {e}"
                self.logger.error(error_msg)
                GLib.idle_add(callback, False, error_msg)
            except Exception as e:
                self.logger.exception(f"Error building application: {e}")
                GLib.idle_add(callback, False, str(e))

        thread = threading.Thread(target=build_app, daemon=True)
        thread.start()

    def install_app_on_device_async(self, callback: Callable[[bool, str], None]) -> None:
        """Install the built application on the target device."""
        def install_app():
            try:
                self.logger.info("Installing application on device")

                install_script = f"""
                cd {self.workspace_container}/{JELLYFIN_REPO_DIR}
                {TIZEN_TOOLS_PATH} install -n {JELLYFIN_APP_FILENAME} -t {DEFAULT_DEVICE_ID}
                """

                self.logger.debug("Executing install script")
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 'bash', '-c', install_script],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_DOCKER_EXEC_MEDIUM
                )

                if result.returncode == 0:
                    self.logger.info("Application installed successfully")
                    GLib.idle_add(callback, True, "Application installed successfully")
                else:
                    error_msg = f"Installation failed: {result.stderr}"
                    self.logger.error(error_msg)
                    GLib.idle_add(callback, False, error_msg)

            except subprocess.TimeoutExpired as e:
                error_msg = f"Installation timed out: {e}"
                self.logger.error(error_msg)
                GLib.idle_add(callback, False, error_msg)
            except Exception as e:
                self.logger.exception(f"Error installing application: {e}")
                GLib.idle_add(callback, False, str(e))

        thread = threading.Thread(target=install_app, daemon=True)
        thread.start()

    def stop_all_processes(self) -> None:
        """Stop all running Docker processes."""
        try:
            self.logger.info(f"Stopping Docker container: {self.container_name}")
            subprocess.run(
                ['docker', 'stop', self.container_name],
                capture_output=True,
                timeout=TIMEOUT_DOCKER_STOP
            )
            self.logger.info("Docker container stopped successfully")
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout stopping container {self.container_name}")
        except FileNotFoundError:
            self.logger.error("Docker executable not found")
        except Exception as e:
            self.logger.exception(f"Error stopping Docker container: {e}")
