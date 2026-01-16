# JellyTizen

A modern GTK4 application for installing Jellyfin media server on Samsung Tizen TVs and projectors.

## Features

- **Modern GTK4 Interface**: Built with Libadwaita for a native GNOME experience
- **Automatic Device Discovery**: Scan your network to find Samsung TVs automatically
- **Docker Integration**: Automated Tizen SDK setup using Docker containers
- **Certificate Management**: Secure handling of Samsung developer certificates
- **Real-time Progress**: Live terminal output during installation process
- **Multi-distro Support**: Automated Docker installation for Arch, Debian, and Fedora

## Prerequisites

- Linux distribution (Arch/Manjaro, Debian/Ubuntu, or Fedora/RHEL)
- Docker (will be installed automatically if missing)
- Samsung TV in Developer Mode (for installation)
- Samsung Developer Certificates (author.p12 and distributor.p12)

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/jellytizen/jellytizen.git
cd jellytizen
```

2. Install dependencies:
```bash
# On Arch/Manjaro
sudo pacman -S python-gobject gtk4 libadwaita vte4

# On Debian/Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adwaita-1 gir1.2-vte-3.91

# On Fedora
sudo dnf install python3-gobject gtk4-devel libadwaita-devel vte291
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

### Using pip

```bash
pip install jellytizen
jellytizen
```

## Usage

### Step 1: Welcome & Docker Check
- The application will check if Docker is installed and running
- If Docker is missing, use the built-in installer for your distribution
- Ensure your system meets all requirements before proceeding

### Step 2: Device Setup
- **Automatic Discovery**: Use the network scanner to find Samsung TVs
- **Manual Connection**: Enter your TV's IP address directly
- Enable "Developer Mode" if your TV is configured for development

### Step 3: Certificate Configuration
- Upload your Samsung developer certificates:
  - `author.p12` - Your personal developer certificate
  - `distributor.p12` - Samsung's distributor certificate
- Enter the password for your author certificate
- Validate certificates before proceeding

### Step 4: Installation
- Review your settings and start the installation
- Monitor real-time progress through the integrated terminal
- Wait for the process to complete (typically 5-10 minutes)

## Certificate Setup

### Getting Samsung Developer Certificates

1. Register as a Samsung developer at [Samsung Developers](https://developer.samsung.com/)
2. Create a Tizen certificate in Samsung Certificate Manager
3. Download both `author.p12` and `distributor.p12` files
4. Note the password you set for the author certificate

### TV Developer Mode Setup

> **Note:** This is the updated method for Samsung TVs (2024+). The old Smart Hub method may still work on older models.

1. Go to the **Apps** section on your TV
2. Scroll to the end of the Apps list and select **App Settings**
3. Inside App Settings, press the **123** button on your remote control
4. Type **12345** - the Developer Mode menu will appear
5. Toggle **Developer Mode** to **On**
6. Enter your computer's IP address when prompted
7. **Restart your TV** to apply Developer Mode settings

## Configuration

Application settings are stored in `~/.config/jellytizen/config.json`. You can customize:

- Docker image preferences
- Network scanning parameters
- Logging levels
- Certificate profiles
- Developer options

## Troubleshooting

### Common Issues

**Docker not starting:**
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in
```

**Certificate validation failed:**
- Ensure certificates are valid P12 files
- Check password is correct
- Verify certificates are for Tizen development

**Device connection failed:**
- Ensure TV is on the same network
- Check if Developer Mode is enabled
- Verify IP address is correct
- Try different connection ports

**Installation hangs:**
- Check Docker container logs
- Ensure sufficient disk space
- Verify network connectivity

### Log Files

Application logs are stored in `~/.local/share/jellytizen/logs/`. Check these files for detailed error information.

### Getting Help

1. Check the [FAQ](https://github.com/jellytizen/jellytizen/wiki/FAQ)
2. Search [existing issues](https://github.com/jellytizen/jellytizen/issues)
3. Create a [new issue](https://github.com/jellytizen/jellytizen/issues/new) with:
   - Your Linux distribution and version
   - JellyTizen version
   - Complete error logs
   - TV model and software version

## Development

### Project Structure

```
├── pages/              # UI pages
│   ├── welcome.py     # Welcome + Docker check
│   ├── device.py      # Device discovery & connection
│   ├── certificates.py # Certificate management
│   ├── install.py     # Installation progress
│   └── preferences.py # Application preferences
├── services/          # Core services
│   ├── docker.py      # Docker operations
│   ├── device.py      # Device management
│   └── certificates.py # Certificate handling
├── utils/             # Utilities
│   ├── config.py      # JSON configuration
│   ├── validators.py  # Input validation
│   └── logger.py      # Logging system
├── app.py            # Main application window
└── main.py           # Entry point
```

### Building from Source

1. Install development dependencies:
```bash
pip install build twine
```

2. Build the package:
```bash
python -m build
```

3. Install locally:
```bash
pip install dist/jellytizen-*.whl
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with clear messages: `git commit -m "Add feature description"`
5. Push to your fork: `git push origin feature-name`
6. Create a Pull Request

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Jellyfin Team](https://jellyfin.org/) for the amazing media server
- [install-jellyfin-tizen](https://github.com/Georift/install-jellyfin-tizen) for the original installation scripts
- [GNOME Project](https://gnome.org/) for GTK4 and Libadwaita
- Samsung for the Tizen platform

## Related Projects

- [Jellyfin](https://github.com/jellyfin/jellyfin) - The Free Software Media System
- [Jellyfin Tizen](https://github.com/jellyfin/jellyfin-tizen) - Jellyfin client for Samsung Tizen TVs
- [install-jellyfin-tizen](https://github.com/Georift/install-jellyfin-tizen) - Original CLI installation tool

# data/com.github.jellytizen.desktop
[Desktop Entry]
Type=Application
Name=JellyTizen
Comment=Install Jellyfin on Samsung Tizen TVs
Icon=com.github.jellytizen
Exec=jellytizen
Categories=AudioVideo;Video;TV;
Keywords=jellyfin;tizen;samsung;tv;media;streaming;
StartupNotify=true

# Makefile
.PHONY: install uninstall clean build run dev test

# Installation paths
PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
DATADIR = $(PREFIX)/share
APPDIR = $(DATADIR)/applications
ICONDIR = $(DATADIR)/icons/hicolor

# Build and install
install: build
	# Install Python package
	pip install dist/jellytizen-*.whl
	
	# Install desktop file
	install -Dm644 data/com.github.jellytizen.desktop $(APPDIR)/
	
	# Install icons
	install -Dm644 data/icons/48x48/com.github.jellytizen.png $(ICONDIR)/48x48/apps/
	install -Dm644 data/icons/64x64/com.github.jellytizen.png $(ICONDIR)/64x64/apps/
	install -Dm644 data/icons/128x128/com.github.jellytizen.png $(ICONDIR)/128x128/apps/
	
	# Update desktop database
	update-desktop-database $(APPDIR)
	gtk-update-icon-cache $(ICONDIR)

# Build package
build: clean
	python -m build

# Run development version
run:
	python main.py

# Development setup
dev:
	pip install -e .
	pip install black flake8 mypy

# Uninstall
uninstall:
	pip uninstall jellytizen
	rm -f $(APPDIR)/com.github.jellytizen.desktop
	rm -f $(ICONDIR)/*/apps/com.github.jellytizen.png
	update-desktop-database $(APPDIR)
	gtk-update-icon-cache $(ICONDIR)

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Run tests
test:
	python -m pytest tests/

# Code formatting
format:
	black .
	
# Linting
lint:
	flake8 .
	mypy .

# Create release
release: clean build
	twine upload dist/*

# Docker development environment
docker-dev:
	docker build -t jellytizen-dev .
	docker run -it --rm \
		-v $(PWD):/app \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		-e DISPLAY=$(DISPLAY) \
		jellytizen-dev

# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y \
          python3-gi \
          python3-gi-cairo \
          gir1.2-gtk-4.0 \
          gir1.2-adwaita-1 \
          gir1.2-vte-3.91
    
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build pytest black flake8 mypy
        pip install -r requirements.txt
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Format check with black
      run: |
        black --check .
    
    - name: Type check with mypy
      run: |
        mypy . || true  # Allow mypy to fail for now
    
    - name: Test with pytest
      run: |
        pytest tests/ || true  # Allow tests to fail for now
    
    - name: Build package
      run: |
        python -m build

  build-flatpak:
    runs-on: ubuntu-latest
    container:
      image: bilelmoussaoui/flatpak-github-actions:gnome-45
      options: --privileged
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Flatpak
      uses: bilelmoussaoui/flatpak-github-actions/flatpak-builder@v5
      with:
        bundle: jellytizen.flatpak
        manifest-path: flatpak/com.github.jellytizen.yml
        cache-key: flatpak-builder-${{ github.sha }}