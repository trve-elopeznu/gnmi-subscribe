#!/usr/bin/env python3
"""
SSH Commit Trigger Script
Python 3.9.20 compatible

This script connects to a router via SSH and performs multiple commits
on a loopback10 interface to trigger DB_COMMIT logs.
"""

import paramiko
import time
import json
import sys
from datetime import datetime
from typing import Optional, Tuple


def load_credentials(credentials_file: str = "gnmi_credentials.json") -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load host, username and password from a JSON credentials file.
    
    Args:
        credentials_file: Path to the JSON file containing credentials
        
    Returns:
        Tuple of (host, username, password) or (None, None, None) if file not found
    """
    try:
        with open(credentials_file, "r") as f:
            creds = json.load(f)
            return creds.get("host"), creds.get("username"), creds.get("password")
    except FileNotFoundError:
        print(f"Error: Credentials file '{credentials_file}' not found")
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in credentials file: {e}")
        return None, None, None


def send_command(shell, command: str, wait_time: float = 0.5) -> str:
    """
    Send a command to the SSH shell and return the output.
    
    Args:
        shell: Paramiko shell channel
        command: Command to send
        wait_time: Time to wait for response
        
    Returns:
        Output from the command
    """
    shell.send(command + "\n")
    time.sleep(wait_time)
    output = ""
    while shell.recv_ready():
        output += shell.recv(65535).decode("utf-8")
    return output


def run_ssh_commits(
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None,
    credentials_file: str = "gnmi_credentials.json",
    num_commits: int = 4,
    wait_between_commits: float = 0.5,
    interface_name: str = "Loopback10",
    verbose: bool = True
) -> None:
    """
    Connect to router via SSH and perform multiple commits on loopback interface.
    
    Args:
        host: Router IP address
        port: SSH port (default 22)
        username: SSH username
        password: SSH password
        credentials_file: Path to JSON credentials file
        num_commits: Number of commits to perform
        wait_between_commits: Wait time in seconds between commits
        interface_name: Name of the loopback interface to configure
        verbose: Print detailed output
    """
    
    # Load credentials from file if not provided
    file_host, file_user, file_pass = load_credentials(credentials_file)
    if not host:
        host = file_host
    if not username:
        username = file_user
    if not password:
        password = file_pass
    
    if not host:
        print("Error: Host is required (set in credentials file or via --address)")
        sys.exit(1)
    
    if not username or not password:
        print("Error: Username and password are required")
        sys.exit(1)
    
    print(f"SSH Commit Trigger Script")
    print(f"=" * 60)
    print(f"Target: {host}:{port}")
    print(f"Interface: {interface_name}")
    print(f"Number of commits: {num_commits}")
    print(f"Wait between commits: {wait_between_commits}s")
    print(f"=" * 60)
    
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the router
        print(f"\n[{datetime.now().isoformat()}] Connecting to {host}...")
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=30
        )
        print(f"[{datetime.now().isoformat()}] Connected successfully!")
        
        # Get interactive shell
        shell = client.invoke_shell()
        time.sleep(1)
        
        # Clear initial output
        if shell.recv_ready():
            shell.recv(65535)
        
        # Enter configuration mode
        print(f"\n[{datetime.now().isoformat()}] Entering configuration mode...")
        output = send_command(shell, "configure terminal", wait_time=1)
        if verbose:
            print(f"  Output: {output.strip()}")
        
        # Create loopback interface first (if it doesn't exist)
        print(f"\n[{datetime.now().isoformat()}] Configuring {interface_name}...")
        output = send_command(shell, f"interface {interface_name}", wait_time=0.5)
        if verbose:
            print(f"  Output: {output.strip()}")
        
        # Perform commits with different descriptions
        commit_times = []
        
        for i in range(1, num_commits + 1):
            timestamp = datetime.now()
            description = f"Commit-Test-{i}-{timestamp.strftime('%Y%m%d-%H%M%S.%f')[:-3]}"
            
            print(f"\n[{timestamp.isoformat()}] Commit {i}/{num_commits}")
            print(f"  Setting description: {description}")
            
            # Set description
            output = send_command(shell, f"description {description}", wait_time=0.3)
            if verbose and output.strip():
                print(f"  Config output: {output.strip()}")
            
            # Exit interface config to commit
            output = send_command(shell, "root", wait_time=0.3)
            
            # Commit the change
            commit_start = datetime.now()
            output = send_command(shell, "commit", wait_time=1.5)
            commit_end = datetime.now()
            commit_duration = (commit_end - commit_start).total_seconds()
            commit_times.append(commit_duration)
            
            print(f"  Commit completed in {commit_duration:.3f}s")
            if verbose and output.strip():
                # Only show relevant lines
                for line in output.strip().split('\n'):
                    if line.strip() and not line.startswith('RP/'):
                        print(f"  Commit output: {line.strip()}")
            
            # Go back to interface config for next iteration
            if i < num_commits:
                output = send_command(shell, f"interface {interface_name}", wait_time=0.3)
                
                # Wait between commits (minimal wait)
                if wait_between_commits > 0:
                    time.sleep(wait_between_commits)
        
        # Exit configuration mode
        print(f"\n[{datetime.now().isoformat()}] Exiting configuration mode...")
        send_command(shell, "end", wait_time=0.5)
        
        # Summary
        print(f"\n{'=' * 60}")
        print(f"Summary")
        print(f"{'=' * 60}")
        print(f"Total commits: {num_commits}")
        print(f"Average commit time: {sum(commit_times)/len(commit_times):.3f}s")
        print(f"Min commit time: {min(commit_times):.3f}s")
        print(f"Max commit time: {max(commit_times):.3f}s")
        print(f"{'=' * 60}")
        
    except paramiko.AuthenticationException:
        print(f"Error: Authentication failed for {username}@{host}")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"Error: SSH connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()
        print(f"\n[{datetime.now().isoformat()}] Connection closed")


def main():
    """Main entry point with CLI arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Connect to router via SSH and perform multiple commits to trigger DB_COMMIT logs"
    )
    parser.add_argument(
        "-a", "--address",
        default=None,
        help="Router IP address (default: from credentials file)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=22,
        help="SSH port (default: 22)"
    )
    parser.add_argument(
        "-u", "--username",
        help="SSH username"
    )
    parser.add_argument(
        "--password",
        help="SSH password"
    )
    parser.add_argument(
        "-c", "--credentials-file",
        default="gnmi_credentials.json",
        help="Path to JSON credentials file (default: gnmi_credentials.json)"
    )
    parser.add_argument(
        "-n", "--num-commits",
        type=int,
        default=4,
        help="Number of commits to perform (default: 4)"
    )
    parser.add_argument(
        "-w", "--wait",
        type=float,
        default=0.5,
        help="Wait time in seconds between commits (default: 0.5)"
    )
    parser.add_argument(
        "-i", "--interface",
        default="Loopback10",
        help="Loopback interface name (default: Loopback10)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )
    
    args = parser.parse_args()
    
    run_ssh_commits(
        host=args.address,
        port=args.port,
        username=args.username,
        password=args.password,
        credentials_file=args.credentials_file,
        num_commits=args.num_commits,
        wait_between_commits=args.wait,
        interface_name=args.interface,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
