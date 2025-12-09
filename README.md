# gNMI Subscribe & SSH Commit Trigger

A Python-based toolkit for monitoring Cisco IOS-XR devices using gNMI subscriptions and triggering configuration commits via SSH to capture DB_COMMIT syslog events.

## 🎯 Overview

This project provides scripts to:
1. **Subscribe to gNMI telemetry** from Cisco IOS-XR devices
2. **Trigger SSH commits** to generate DB_COMMIT events
3. **Run both in parallel** to capture commit events in real-time
4. **Filter and analyze** DB_COMMIT entries from syslog output

Perfect for testing gNMI subscriptions, analyzing configuration commit behavior, and validating telemetry delivery.

## ✨ Features

- **gNMI Subscription**: Subscribe to any YANG model path and capture telemetry data
- **SSH Commit Trigger**: Automatically perform multiple configuration commits
- **Parallel Execution**: Run both operations simultaneously to capture events
- **DB_COMMIT Analysis**: Extract and analyze commit IDs with duplicate detection
- **Configurable**: All settings in a single JSON configuration file
- **Dependency Checker**: Validate environment before running

## 📋 Requirements

### System Requirements
- **Python**: ≥ 3.9
- **UV**: Fast Python package manager ([Installation guide](https://docs.astral.sh/uv/))
- **gnmic**: gNMI client tool ([Installation guide](https://gnmic.openconfig.net/install/))

### Python Dependencies
- `paramiko` (for SSH connections)

All Python dependencies are managed via UV and defined in `pyproject.toml`.

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/trve-elopeznu/gnmi-subscribe.git
cd gnmi-subscribe
```

### 2. Install UV (if not already installed)
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

### 3. Set Up the Project
```bash
# Initialize UV virtual environment and install dependencies
uv sync
```

### 4. Configure Credentials
```bash
# Copy the example configuration
cp gnmi_credentials.example.json gnmi_credentials.json

# Edit with your device details
nano gnmi_credentials.json  # or your preferred editor
```

### 5. Verify Setup
```bash
# Run dependency checker
uv run python check_dependencies.py
```

### 6. Run Scripts
```bash
# Run both gNMI subscription and SSH commits in parallel
uv run python run_parallel.py

# Or run scripts individually
uv run python gnmi_subscribe.py
uv run python ssh_commit_trigger.py
uv run python filter_db_commit.py
```

## 📝 Configuration

### Main Configuration File: `gnmi_credentials.json`

This file contains all settings for your environment:

```json
{
    "host": "10.105.209.144",
    "username": "cisco",
    "password": "cisco",
    "gnmi": {
        "port": 57344,
        "path": "Cisco-IOS-XR-infra-syslog-oper:/syslog/messages/message/text",
        "duration": 120,
        "timeout": "60s",
        "output_file": "syslog_output.log"
    },
    "ssh": {
        "port": 22,
        "num_commits": 5,
        "wait_between_commits": 0.5,
        "interface": "Loopback10",
        "delay_before_start": 5
    }
}
```

### Configuration Parameters

#### General Settings
| Parameter | Description | Example |
|-----------|-------------|---------|
| `host` | Target device IP address or hostname | `"10.105.209.144"` |
| `username` | Device username | `"cisco"` |
| `password` | Device password | `"cisco"` |

#### gNMI Settings (`gnmi` section)
| Parameter | Description | Default |
|-----------|-------------|---------|
| `port` | gNMI port | `57344` |
| `path` | YANG model path to subscribe | `"Cisco-IOS-XR-infra-syslog-oper:/syslog/messages/message/text"` |
| `duration` | Subscription duration (seconds) | `120` |
| `timeout` | Connection timeout | `"60s"` |
| `output_file` | Output log file name | `"syslog_output.log"` |

#### SSH Settings (`ssh` section)
| Parameter | Description | Default |
|-----------|-------------|---------|
| `port` | SSH port | `22` |
| `num_commits` | Number of commits to trigger | `5` |
| `wait_between_commits` | Wait time between commits (seconds) | `0.5` |
| `interface` | Interface to modify for commits | `"Loopback10"` |
| `delay_before_start` | Delay before starting SSH (seconds) | `5` |

### Common YANG Paths

Here are some useful YANG model paths for Cisco IOS-XR:

```json
// Syslog messages
"Cisco-IOS-XR-infra-syslog-oper:/syslog/messages/message/text"

// Interface statistics
"Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces"

// BGP neighbor state
"Cisco-IOS-XR-ipv4-bgp-oper:/bgp/instances/instance/instance-active/default-vrf/neighbors"

// CPU utilization
"Cisco-IOS-XR-wdsysmon-fd-oper:/system-monitoring/cpu-utilization"
```

## 🛠️ Scripts

### 1. `run_parallel.py` - Parallel Runner
Run gNMI subscription and SSH commits simultaneously.

```bash
# Use config file defaults
uv run python run_parallel.py

# Show current configuration
uv run python run_parallel.py --show-config

# Override specific options
uv run python run_parallel.py -d 300 -n 10

# Custom output file
uv run python run_parallel.py -o my_output.log

# Quiet mode
uv run python run_parallel.py -q
```

**Options:**
- `-d, --duration`: Subscription duration in seconds
- `-n, --num-commits`: Number of SSH commits
- `-o, --output`: Output file name
- `--gnmi-path`: Override YANG path
- `-q, --quiet`: Suppress verbose output
- `--show-config`: Display current configuration

### 2. `gnmi_subscribe.py` - gNMI Subscription
Subscribe to gNMI telemetry and save output.

```bash
# Use config file settings
uv run python gnmi_subscribe.py

# Custom path and duration
uv run python gnmi_subscribe.py \
    --path "Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces" \
    -d 300 -o stats.log

# Specify target explicitly
uv run python gnmi_subscribe.py -a 10.1.1.1:57344
```

**Options:**
- `-a, --address`: Target address (ip:port)
- `--port`: gNMI port (when using host from config)
- `-p, --path`: YANG model path
- `-d, --duration`: Subscription duration (seconds)
- `-o, --output`: Output file
- `-t, --timeout`: Connection timeout

### 3. `ssh_commit_trigger.py` - SSH Commit Trigger
Trigger multiple configuration commits via SSH.

```bash
# Use config file settings
uv run python ssh_commit_trigger.py

# Custom number of commits
uv run python ssh_commit_trigger.py -n 10

# Different interface
uv run python ssh_commit_trigger.py -i Loopback20

# Quiet mode
uv run python ssh_commit_trigger.py -n 5 -q
```

**Options:**
- `-n, --num-commits`: Number of commits
- `-w, --wait`: Wait time between commits (seconds)
- `-i, --interface`: Interface to modify
- `-a, --address`: Device IP (overrides config)
- `-q, --quiet`: Suppress verbose output

### 4. `filter_db_commit.py` - DB_COMMIT Analyzer
Extract and analyze DB_COMMIT entries from log files.

```bash
# Analyze default log file
uv run python filter_db_commit.py

# Verbose output
uv run python filter_db_commit.py -v

# Custom input/output
uv run python filter_db_commit.py -i my_log.log -o report.md

# Also export as JSON
uv run python filter_db_commit.py --json
```

**Options:**
- `-i, --input`: Input log file
- `-o, --output`: Output markdown report
- `--json`: Also output as JSON
- `-v, --verbose`: Print detailed output

### 5. `check_dependencies.py` - Dependency Checker
Validate environment and dependencies.

```bash
uv run python check_dependencies.py
```

Checks:
- Python version
- Virtual environment
- Python packages
- External tools (gnmic, uv)
- Project files
- Configuration file
- Network connectivity

## 📊 Example Workflow

### Complete Test Scenario

```bash
# 1. Verify environment
uv run python check_dependencies.py

# 2. Configure for your device
nano gnmi_credentials.json

# 3. Run parallel test (2 minutes, 5 commits)
uv run python run_parallel.py -d 120 -n 5

# 4. Analyze results
uv run python filter_db_commit.py -v

# 5. View the report
cat db_commit_report.md
```

### Output Files

After running the scripts, you'll have:

- **`syslog_output.log`**: Raw gNMI subscription data with timestamps
- **`db_commit_report.md`**: Markdown report with commit analysis
- **`db_commit_report.json`**: JSON data (if `--json` flag used)

## 🔧 Customization Guide

### Changing the Target Device

Edit `gnmi_credentials.json`:
```json
{
    "host": "YOUR_DEVICE_IP",
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD"
}
```

### Changing the YANG Model Path

Edit the `gnmi.path` in `gnmi_credentials.json`:
```json
{
    "gnmi": {
        "path": "YOUR_YANG_PATH_HERE"
    }
}
```

### Changing Subscription Duration

Edit `gnmi.duration` (in seconds):
```json
{
    "gnmi": {
        "duration": 600  // 10 minutes
    }
}
```

### Changing Number of Commits

Edit `ssh.num_commits`:
```json
{
    "ssh": {
        "num_commits": 10
    }
}
```

### Changing gNMI Port

Edit `gnmi.port`:
```json
{
    "gnmi": {
        "port": 57400  // Custom port
    }
}
```

### Using a Different Interface

Edit `ssh.interface`:
```json
{
    "ssh": {
        "interface": "Loopback99"
    }
}
```

## 📁 Project Structure

```
gnmi-subscribe/
├── gnmi_subscribe.py           # gNMI subscription script
├── ssh_commit_trigger.py       # SSH commit trigger script
├── run_parallel.py             # Parallel runner wrapper
├── filter_db_commit.py         # DB_COMMIT analyzer
├── check_dependencies.py       # Dependency checker
├── gnmi_credentials.json       # Your config (gitignored)
├── gnmi_credentials.example.json  # Example config
├── pyproject.toml              # Python project config
├── uv.lock                     # Dependency lock file
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🔒 Security

- **Credentials**: The actual `gnmi_credentials.json` is gitignored
- **Logs**: Output files (`*.log`) are gitignored
- **Example file**: Only contains placeholders

**Never commit real credentials to version control!**

## 🐛 Troubleshooting

### "gnmic command not found"
```bash
# macOS
brew install gnmic

# Or download from https://gnmic.openconfig.net/install/
```

### "uv: command not found"
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # or ~/.bashrc
```

### "Connection timeout"
- Verify device IP is correct
- Check network connectivity: `ping <device_ip>`
- Verify gNMI port is correct (default: 57344)
- Check firewall rules

### "Authentication failed"
- Verify username/password in `gnmi_credentials.json`
- Ensure the user has proper permissions on the device

### "Module not found"
```bash
# Reinstall dependencies
uv sync
```

## 📚 Additional Resources

- [gNMIc Documentation](https://gnmic.openconfig.net/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [Cisco IOS-XR YANG Models](https://github.com/YangModels/yang/tree/main/vendor/cisco/xr)
- [OpenConfig YANG Models](https://github.com/openconfig/public)

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📄 License

This project is provided as-is for testing and development purposes.

## 👤 Author

Created by Eduardo Lopez for gNMI subscription testing and analysis.

---

**Quick Links:**
- [Issues](https://github.com/trve-elopeznu/gnmi-subscribe/issues)
- [Latest Release](https://github.com/trve-elopeznu/gnmi-subscribe/releases)
