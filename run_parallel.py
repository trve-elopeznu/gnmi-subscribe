#!/usr/bin/env python3
"""
Parallel Runner Script
Runs gnmi_subscribe.py and ssh_commit_trigger.py in parallel.

This script starts the gNMI subscription first, waits for it to connect,
then triggers SSH commits while capturing syslog data.

Configuration can be loaded from gnmi_credentials.json or passed via CLI.
"""

import subprocess
import sys
import time
import argparse
import signal
import json
from datetime import datetime
from typing import Optional, Dict, Any


def load_config(credentials_file: str = "gnmi_credentials.json") -> Dict[str, Any]:
    """
    Load configuration from JSON credentials file.
    
    Args:
        credentials_file: Path to the JSON file containing configuration
        
    Returns:
        Dictionary with configuration values
    """
    config = {
        "host": None,
        "username": None,
        "password": None,
        "gnmi": {
            "port": 57344,
            "path": "Cisco-IOS-XR-infra-syslog-oper:/syslog/messages/message/text",
            "duration": 600,
            "timeout": "60s",
            "output_file": None
        },
        "ssh": {
            "port": 22,
            "num_commits": 5,
            "wait_between_commits": 0.5,
            "interface": "Loopback10",
            "delay_before_start": 5
        }
    }
    
    try:
        with open(credentials_file, "r") as f:
            file_config = json.load(f)
            
            # Update base config
            config["host"] = file_config.get("host", config["host"])
            config["username"] = file_config.get("username", config["username"])
            config["password"] = file_config.get("password", config["password"])
            
            # Update gNMI config
            if "gnmi" in file_config:
                config["gnmi"].update(file_config["gnmi"])
            
            # Update SSH config
            if "ssh" in file_config:
                config["ssh"].update(file_config["ssh"])
                
    except FileNotFoundError:
        print(f"Warning: Config file '{credentials_file}' not found, using defaults")
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in config file: {e}")
    
    return config


def run_parallel(
    # gNMI subscribe options
    gnmi_path: str = "Cisco-IOS-XR-infra-syslog-oper:/syslog/messages/message/text",
    gnmi_output: str = None,
    gnmi_timeout: str = "60s",
    gnmi_duration: int = 600,
    gnmi_stream_mode: str = "sample",
    # SSH commit options
    ssh_num_commits: int = 5,
    ssh_wait: float = 0.5,
    ssh_interface: str = "Loopback10",
    ssh_delay: int = 5,
    # Common options
    credentials_file: str = "gnmi_credentials.json",
    verbose: bool = True
) -> None:
    """
    Run gNMI subscribe and SSH commit trigger in parallel.
    
    Args:
        gnmi_path: gNMI path to subscribe to
        gnmi_output: Output file for gNMI subscription
        gnmi_timeout: Connection timeout for gNMI
        gnmi_duration: Duration in seconds for gNMI subscription
        gnmi_stream_mode: Stream mode (sample, on_change, target_defined)
        ssh_num_commits: Number of SSH commits to perform
        ssh_wait: Wait time between commits
        ssh_interface: Loopback interface to configure
        ssh_delay: Delay in seconds before starting SSH commits
        credentials_file: Path to credentials JSON file
        verbose: Print detailed output
    """
    
    gnmi_process: Optional[subprocess.Popen] = None
    ssh_process: Optional[subprocess.Popen] = None
    
    def cleanup(signum=None, frame=None):
        """Clean up processes on exit."""
        print(f"\n[{datetime.now().isoformat()}] Cleaning up processes...")
        if gnmi_process and gnmi_process.poll() is None:
            gnmi_process.terminate()
            try:
                gnmi_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gnmi_process.kill()
        if ssh_process and ssh_process.poll() is None:
            ssh_process.terminate()
            try:
                ssh_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ssh_process.kill()
        print(f"[{datetime.now().isoformat()}] Cleanup complete")
        if signum:
            sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("=" * 70)
    print("Parallel Runner - gNMI Subscribe + SSH Commit Trigger")
    print("=" * 70)
    print(f"Start Time: {datetime.now().isoformat()}")
    print()
    print("gNMI Subscribe Settings:")
    print(f"  Path: {gnmi_path}")
    print(f"  Output: {gnmi_output if gnmi_output else 'auto-generated in results/'}")
    print(f"  Duration: {gnmi_duration}s ({gnmi_duration // 60} minutes)")
    print(f"  Timeout: {gnmi_timeout}")
    print(f"  Stream Mode: {gnmi_stream_mode}")
    print()
    print("SSH Commit Settings:")
    print(f"  Number of commits: {ssh_num_commits}")
    print(f"  Wait between commits: {ssh_wait}s")
    print(f"  Interface: {ssh_interface}")
    print(f"  Delay before starting: {ssh_delay}s")
    print("=" * 70)
    
    try:
        # Build gNMI subscribe command
        gnmi_cmd = [
            sys.executable, "gnmi_subscribe.py",
            "--path", gnmi_path,
            "-t", gnmi_timeout,
            "--duration", str(gnmi_duration),
            "-s", gnmi_stream_mode,
            "-c", credentials_file
        ]
        
        # Only add output file if specified
        if gnmi_output:
            gnmi_cmd.extend(["-o", gnmi_output])
        
        # Start gNMI subscription
        print(f"\n[{datetime.now().isoformat()}] Starting gNMI subscription...")
        gnmi_process = subprocess.Popen(
            gnmi_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Wait for gNMI to connect before starting SSH commits
        print(f"[{datetime.now().isoformat()}] Waiting {ssh_delay}s for gNMI to establish connection...")
        time.sleep(ssh_delay)
        
        # Check if gNMI process is still running
        if gnmi_process.poll() is not None:
            print(f"[{datetime.now().isoformat()}] ERROR: gNMI subscription failed to start")
            # Read any error output
            stdout, _ = gnmi_process.communicate()
            if stdout:
                print(f"Output: {stdout}")
            sys.exit(1)
        
        # Build SSH commit command
        ssh_cmd = [
            sys.executable, "ssh_commit_trigger.py",
            "-n", str(ssh_num_commits),
            "-w", str(ssh_wait),
            "-i", ssh_interface,
            "-c", credentials_file
        ]
        
        # Start SSH commits
        print(f"[{datetime.now().isoformat()}] Starting SSH commit trigger ({ssh_num_commits} commits)...")
        ssh_process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Monitor both processes
        print(f"\n[{datetime.now().isoformat()}] Both processes running. Monitoring...")
        print("-" * 70)
        
        # Wait for SSH process to complete while monitoring gNMI
        ssh_output_lines = []
        while ssh_process.poll() is None:
            # Read SSH output
            line = ssh_process.stdout.readline()
            if line:
                ssh_output_lines.append(line)
                if verbose:
                    print(f"[SSH] {line.rstrip()}")
            
            # Check if gNMI is still running
            if gnmi_process.poll() is not None:
                print(f"\n[{datetime.now().isoformat()}] WARNING: gNMI subscription ended unexpectedly")
                break
            
            time.sleep(0.1)
        
        # Get remaining SSH output
        remaining_output, _ = ssh_process.communicate()
        if remaining_output:
            for line in remaining_output.split('\n'):
                if line:
                    ssh_output_lines.append(line + '\n')
                    if verbose:
                        print(f"[SSH] {line}")
        
        ssh_exit_code = ssh_process.returncode
        print("-" * 70)
        print(f"\n[{datetime.now().isoformat()}] SSH commits completed (exit code: {ssh_exit_code})")
        
        # Check how long gNMI should continue
        print(f"[{datetime.now().isoformat()}] gNMI subscription still running...")
        print(f"[{datetime.now().isoformat()}] Press Ctrl+C to stop early, or wait for duration to complete")
        
        # Wait for gNMI to finish or user interrupt
        gnmi_output_lines = []
        while gnmi_process.poll() is None:
            line = gnmi_process.stdout.readline()
            if line:
                gnmi_output_lines.append(line)
                if verbose and "Received" in line:
                    print(f"[gNMI] {line.rstrip()}")
            time.sleep(0.1)
        
        # Get remaining gNMI output
        remaining_output, _ = gnmi_process.communicate()
        if remaining_output:
            gnmi_output_lines.extend(remaining_output.split('\n'))
        
        gnmi_exit_code = gnmi_process.returncode
        
        # Summary
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"End Time: {datetime.now().isoformat()}")
        print(f"gNMI Subscription: {'Success' if gnmi_exit_code == 0 else f'Failed (exit code: {gnmi_exit_code})'}")
        print(f"SSH Commits: {'Success' if ssh_exit_code == 0 else f'Failed (exit code: {ssh_exit_code})'}")
        print(f"Output saved to: {gnmi_output}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[{datetime.now().isoformat()}] ERROR: {e}")
        cleanup()
        sys.exit(1)
    finally:
        cleanup()


def main():
    """Main entry point with CLI arguments."""
    # Pre-parse to get credentials file first
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--credentials-file", default="gnmi_credentials.json")
    pre_args, _ = pre_parser.parse_known_args()
    
    # Load config from file
    config = load_config(pre_args.credentials_file)
    gnmi_config = config["gnmi"]
    ssh_config = config["ssh"]
    
    parser = argparse.ArgumentParser(
        description="Run gNMI subscribe and SSH commit trigger in parallel. "
                    "Settings can be configured in gnmi_credentials.json or overridden via CLI."
    )
    
    # gNMI options
    gnmi_group = parser.add_argument_group("gNMI Subscribe Options")
    gnmi_group.add_argument(
        "--gnmi-path",
        default=gnmi_config.get("path"),
        help=f"gNMI path to subscribe to (config: {gnmi_config.get('path')})"
    )
    gnmi_group.add_argument(
        "-o", "--output",
        default=None,
        help="Output file for gNMI subscription (default: auto-generated timestamp in results/)"
    )
    gnmi_group.add_argument(
        "-t", "--timeout",
        default=gnmi_config.get("timeout"),
        help=f"gNMI connection timeout (config: {gnmi_config.get('timeout')})"
    )
    gnmi_group.add_argument(
        "-d", "--duration",
        type=int,
        default=gnmi_config.get("duration"),
        help=f"gNMI subscription duration in seconds (config: {gnmi_config.get('duration')})"
    )
    gnmi_group.add_argument(
        "-s", "--stream-mode",
        default="sample",
        choices=["sample", "on_change", "target_defined"],
        help="Stream mode for gNMI subscription (default: sample)"
    )
    
    # SSH options
    ssh_group = parser.add_argument_group("SSH Commit Options")
    ssh_group.add_argument(
        "-n", "--num-commits",
        type=int,
        default=ssh_config.get("num_commits"),
        help=f"Number of SSH commits (config: {ssh_config.get('num_commits')})"
    )
    ssh_group.add_argument(
        "-w", "--wait",
        type=float,
        default=ssh_config.get("wait_between_commits"),
        help=f"Wait time between commits in seconds (config: {ssh_config.get('wait_between_commits')})"
    )
    ssh_group.add_argument(
        "-i", "--interface",
        default=ssh_config.get("interface"),
        help=f"Loopback interface to configure (config: {ssh_config.get('interface')})"
    )
    ssh_group.add_argument(
        "--ssh-delay",
        type=int,
        default=ssh_config.get("delay_before_start"),
        help=f"Delay before starting SSH commits in seconds (config: {ssh_config.get('delay_before_start')})"
    )
    
    # Common options
    parser.add_argument(
        "-c", "--credentials-file",
        default="gnmi_credentials.json",
        help="Path to JSON credentials/config file (default: gnmi_credentials.json)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show current configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Show config and exit if requested
    if args.show_config:
        print("Current Configuration:")
        print(json.dumps(config, indent=2))
        sys.exit(0)
    
    run_parallel(
        gnmi_path=args.gnmi_path,
        gnmi_output=args.output,
        gnmi_timeout=args.timeout,
        gnmi_duration=args.duration,
        gnmi_stream_mode=args.stream_mode,
        ssh_num_commits=args.num_commits,
        ssh_wait=args.wait,
        ssh_interface=args.interface,
        ssh_delay=args.ssh_delay,
        credentials_file=args.credentials_file,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
