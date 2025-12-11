.PHONY: help install check sync run-parallel gnmi ssh filter clean test

# Default target
help:
	@echo "=========================================="
	@echo "  gNMI Subscribe - Make Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install       - Install UV and setup project (first time only)"
	@echo "  make sync          - Sync dependencies using uv"
	@echo "  make check         - Check dependencies and configuration"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run-parallel  - Run gNMI subscribe and SSH commits in parallel"
	@echo "  make gnmi          - Run gNMI subscription only"
	@echo "  make ssh           - Run SSH commit trigger only"
	@echo "  make filter        - Filter DB_COMMIT entries from log"
	@echo ""
	@echo "Configuration:"
	@echo "  make config        - Create config file from example"
	@echo "  make show-config   - Display current configuration"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean         - Remove generated files and logs"
	@echo "  make test          - Run quick test (30s duration, 3 commits)"
	@echo "  make logs          - View recent log files"
	@echo ""
	@echo "Examples:"
	@echo "  make run-parallel DURATION=120 COMMITS=5"
	@echo "  make gnmi YANG_PATH='Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces'"
	@echo "  make gnmi STREAM_MODE=on_change DURATION=300"
	@echo "  make ssh COMMITS=10 INTERFACE=Loopback20"
	@echo ""

# Installation
install:
	@echo "Installing UV package manager..."
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "Syncing dependencies..."
	@uv sync
	@echo "Creating config file if needed..."
	@test -f gnmi_credentials.json || cp gnmi_credentials.example.json gnmi_credentials.json
	@echo ""
	@echo "✓ Installation complete!"
	@echo "  Edit gnmi_credentials.json with your device details"
	@echo "  Run 'make check' to verify setup"

# Dependency sync
sync:
	@echo "Syncing dependencies..."
	@uv sync --frozen

# Check dependencies
check:
	@echo "Checking dependencies and configuration..."
	@uv run python check_dependencies.py

# Configuration
config:
	@if [ -f gnmi_credentials.json ]; then \
		echo "⚠ gnmi_credentials.json already exists!"; \
		echo "  Remove it first or edit manually"; \
	else \
		cp gnmi_credentials.example.json gnmi_credentials.json; \
		echo "✓ Created gnmi_credentials.json from example"; \
		echo "  Edit it with your device details"; \
	fi

show-config:
	@uv run python run_parallel.py --show-config

# Run parallel (with optional parameters)
DURATION ?= 600
COMMITS ?= 5
STREAM_MODE ?= sample

run-parallel:
	@echo "Running gNMI subscribe and SSH commits in parallel..."
	@echo "  Duration: $(DURATION)s"
	@echo "  Commits: $(COMMITS)"
	@echo "  Stream Mode: $(STREAM_MODE)"
	@if [ -n "$(OUTPUT)" ]; then \
		uv run python run_parallel.py -d $(DURATION) -n $(COMMITS) -o $(OUTPUT) -s $(STREAM_MODE); \
	else \
		uv run python run_parallel.py -d $(DURATION) -n $(COMMITS) -s $(STREAM_MODE); \
	fi

# gNMI subscribe only
YANG_PATH ?= 
TIMEOUT ?= 60s
STREAM_MODE ?= sample

gnmi:
	@echo "Running gNMI subscription..."
	@if [ -n "$(YANG_PATH)" ] && [ -n "$(OUTPUT)" ]; then \
		echo "  YANG Path: $(YANG_PATH)"; \
		uv run python gnmi_subscribe.py --path "$(YANG_PATH)" -d $(DURATION) -o $(OUTPUT) -t $(TIMEOUT) -s $(STREAM_MODE); \
	elif [ -n "$(YANG_PATH)" ]; then \
		echo "  YANG Path: $(YANG_PATH)"; \
		uv run python gnmi_subscribe.py --path "$(YANG_PATH)" -d $(DURATION) -t $(TIMEOUT) -s $(STREAM_MODE); \
	elif [ -n "$(OUTPUT)" ]; then \
		echo "  YANG Path: (from gnmi_credentials.json)"; \
		uv run python gnmi_subscribe.py -d $(DURATION) -o $(OUTPUT) -t $(TIMEOUT) -s $(STREAM_MODE); \
	else \
		echo "  YANG Path: (from gnmi_credentials.json)"; \
		uv run python gnmi_subscribe.py -d $(DURATION) -t $(TIMEOUT) -s $(STREAM_MODE); \
	fi

# SSH commits only
INTERFACE ?= Loopback10
WAIT ?= 0.5

ssh:
	@echo "Running SSH commit trigger..."
	@echo "  Commits: $(COMMITS)"
	@echo "  Interface: $(INTERFACE)"
	@echo "  Wait: $(WAIT)s"
	@uv run python ssh_commit_trigger.py -n $(COMMITS) -i $(INTERFACE) -w $(WAIT)

# Filter DB_COMMIT
filter:
	@echo "Filtering DB_COMMIT entries..."
	@if [ -n "$(INPUT)" ] && [ -n "$(REPORT)" ]; then \
		echo "  Input: $(INPUT)"; \
		echo "  Report: $(REPORT)"; \
		uv run python filter_db_commit.py -i $(INPUT) -o $(REPORT) -v; \
	elif [ -n "$(INPUT)" ]; then \
		echo "  Input: $(INPUT)"; \
		uv run python filter_db_commit.py -i $(INPUT) -v; \
	else \
		echo "  Auto-detecting latest log file..."; \
		uv run python filter_db_commit.py -v; \
	fi

# Quick test run
test:
	@echo "Running quick test (30s duration, 3 commits)..."
	@uv run python run_parallel.py -d 30 -n 3 -o test_output.log
	@echo ""
	@echo "Analyzing results..."
	@uv run python filter_db_commit.py -i test_output.log -o test_report.md -v
	@echo ""
	@echo "✓ Test complete! Check test_report.md for results"

# View logs
logs:
	@echo "Recent log files:"
	@ls -lht *.log 2>/dev/null || echo "  No log files found"
	@echo ""
	@echo "Recent reports:"
	@ls -lht *_report.md 2>/dev/null || echo "  No report files found"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -f *.log
	@rm -f *_report.md
	@rm -f *_report.json
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned!"

# Advanced: Run with custom config file
CONFIG_FILE ?= gnmi_credentials.json

run-custom:
	@echo "Running with custom config: $(CONFIG_FILE)"
	@uv run python run_parallel.py -c $(CONFIG_FILE)
