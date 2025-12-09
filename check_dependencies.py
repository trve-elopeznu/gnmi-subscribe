#!/usr/bin/env python3
"""
Dependency Check Script
Validates all dependencies required to run the gnmi-subscribe project scripts.

Checks:
- Python version
- Required Python packages
- External tools (gnmic)
- Configuration files
- UV package manager
"""

import sys
import subprocess
import shutil
import json
from pathlib import Path
from typing import Tuple, List, Dict

# Minimum Python version
MIN_PYTHON_VERSION = (3, 9)

# Required Python packages
REQUIRED_PACKAGES = [
    "paramiko",
]

# Required external tools
REQUIRED_TOOLS = [
    ("gnmic", "gnmic --version", "https://gnmic.openconfig.net/install/"),
    ("uv", "uv --version", "https://docs.astral.sh/uv/"),
]

# Required project files
REQUIRED_FILES = [
    "gnmi_subscribe.py",
    "ssh_commit_trigger.py",
    "run_parallel.py",
    "filter_db_commit.py",
    "pyproject.toml",
]

# Configuration file
CONFIG_FILE = "gnmi_credentials.json"
CONFIG_EXAMPLE = "gnmi_credentials.example.json"

# Required config keys
REQUIRED_CONFIG_KEYS = ["host", "username", "password"]


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")


def print_check(name: str, passed: bool, message: str = "") -> None:
    """Print a check result."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status}  {name}")
    if message and not passed:
        print(f"         {Colors.YELLOW}→ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠ WARN{Colors.RESET}  {message}")


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets minimum requirements."""
    current = sys.version_info[:2]
    required = MIN_PYTHON_VERSION
    passed = current >= required
    message = f"Python {current[0]}.{current[1]} (required: >={required[0]}.{required[1]})"
    return passed, message


def check_package_installed(package: str) -> Tuple[bool, str]:
    """Check if a Python package is installed."""
    try:
        __import__(package)
        return True, f"{package} is installed"
    except ImportError:
        return False, f"Install with: uv add {package}"


def check_tool_installed(tool: str, version_cmd: str, install_url: str) -> Tuple[bool, str]:
    """Check if an external tool is installed."""
    if shutil.which(tool):
        try:
            result = subprocess.run(
                version_cmd.split(),
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown version"
            return True, version
        except Exception:
            return True, "installed (version unknown)"
    return False, f"Install from: {install_url}"


def check_file_exists(filepath: str) -> Tuple[bool, str]:
    """Check if a required file exists."""
    path = Path(filepath)
    if path.exists():
        return True, f"Found: {filepath}"
    return False, f"Missing: {filepath}"


def check_config_file() -> Tuple[bool, str, Dict]:
    """Check if configuration file exists and has required keys."""
    config_path = Path(CONFIG_FILE)
    
    if not config_path.exists():
        example_path = Path(CONFIG_EXAMPLE)
        if example_path.exists():
            return False, f"Missing {CONFIG_FILE}. Copy from {CONFIG_EXAMPLE} and update values.", {}
        return False, f"Missing {CONFIG_FILE}. Create it with host, username, password.", {}
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        missing_keys = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
        if missing_keys:
            return False, f"Missing required keys: {', '.join(missing_keys)}", config
        
        # Check for placeholder values
        placeholders = []
        if config.get("username") in ["your_username", ""]:
            placeholders.append("username")
        if config.get("password") in ["your_password", ""]:
            placeholders.append("password")
        
        if placeholders:
            return False, f"Update placeholder values for: {', '.join(placeholders)}", config
        
        return True, f"Valid config with host: {config.get('host', 'unknown')}", config
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", {}
    except Exception as e:
        return False, f"Error reading config: {e}", {}


def check_venv() -> Tuple[bool, str]:
    """Check if running in a virtual environment."""
    venv_path = Path(".venv")
    if venv_path.exists():
        return True, "Virtual environment found (.venv)"
    return False, "Run 'uv sync' to create virtual environment"


def check_network_connectivity(host: str) -> Tuple[bool, str]:
    """Check basic network connectivity to target host."""
    if not host:
        return False, "No host configured"
    
    try:
        # Try to ping the host (just one packet, 2 second timeout)
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", host],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, f"Host {host} is reachable"
        return False, f"Host {host} is not reachable"
    except subprocess.TimeoutExpired:
        return False, f"Timeout connecting to {host}"
    except Exception as e:
        return False, f"Cannot check connectivity: {e}"


def run_checks() -> Tuple[int, int, int]:
    """Run all dependency checks. Returns (passed, failed, warnings)."""
    passed = 0
    failed = 0
    warnings = 0
    
    # Python version
    print_header("Python Environment")
    ok, msg = check_python_version()
    print_check(f"Python version: {msg}", ok)
    if ok:
        passed += 1
    else:
        failed += 1
    
    # Virtual environment
    ok, msg = check_venv()
    print_check("Virtual environment", ok, msg)
    if ok:
        passed += 1
    else:
        failed += 1
    
    # Python packages
    print_header("Python Packages")
    for package in REQUIRED_PACKAGES:
        ok, msg = check_package_installed(package)
        print_check(package, ok, msg)
        if ok:
            passed += 1
        else:
            failed += 1
    
    # External tools
    print_header("External Tools")
    for tool, version_cmd, install_url in REQUIRED_TOOLS:
        ok, msg = check_tool_installed(tool, version_cmd, install_url)
        print_check(f"{tool}: {msg}", ok)
        if ok:
            passed += 1
        else:
            failed += 1
    
    # Project files
    print_header("Project Files")
    for filepath in REQUIRED_FILES:
        ok, msg = check_file_exists(filepath)
        print_check(filepath, ok, msg)
        if ok:
            passed += 1
        else:
            failed += 1
    
    # Configuration
    print_header("Configuration")
    ok, msg, config = check_config_file()
    print_check(CONFIG_FILE, ok, msg)
    if ok:
        passed += 1
    else:
        failed += 1
    
    # Optional: Network connectivity
    print_header("Network Connectivity (Optional)")
    host = config.get("host") if config else None
    if host:
        ok, msg = check_network_connectivity(host)
        if ok:
            print_check(msg, ok)
            passed += 1
        else:
            print_warning(msg)
            warnings += 1
    else:
        print_warning("Skipping network check - no host configured")
        warnings += 1
    
    return passed, failed, warnings


def print_summary(passed: int, failed: int, warnings: int) -> None:
    """Print summary of all checks."""
    print_header("Summary")
    total = passed + failed
    
    print(f"  {Colors.GREEN}Passed:   {passed}/{total}{Colors.RESET}")
    print(f"  {Colors.RED}Failed:   {failed}/{total}{Colors.RESET}")
    print(f"  {Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")
    
    if failed == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ All checks passed! Ready to run scripts.{Colors.RESET}")
        print(f"\n  Quick start:")
        print(f"    uv run python run_parallel.py        # Run gNMI + SSH in parallel")
        print(f"    uv run python gnmi_subscribe.py      # gNMI subscription only")
        print(f"    uv run python ssh_commit_trigger.py  # SSH commits only")
        print(f"    uv run python filter_db_commit.py    # Filter DB_COMMIT from logs")
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}✗ Some checks failed. Please fix the issues above.{Colors.RESET}")
        print(f"\n  Common fixes:")
        print(f"    1. Run 'uv sync' to install dependencies")
        print(f"    2. Copy gnmi_credentials.example.json to gnmi_credentials.json")
        print(f"    3. Update credentials with your actual host/username/password")
        print(f"    4. Install gnmic: brew install gnmic (macOS)")


def main():
    """Main entry point."""
    print(f"\n{Colors.BOLD}gnmi-subscribe Dependency Checker{Colors.RESET}")
    print(f"Validating environment for script execution...\n")
    
    passed, failed, warnings = run_checks()
    print_summary(passed, failed, warnings)
    
    # Exit with error code if any checks failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
