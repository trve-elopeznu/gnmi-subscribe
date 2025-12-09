#!/usr/bin/env python3
"""
gNMIc Subscribe Script
Python 3.9.20 compatible

This script runs a gnmic subscribe command for a specified duration (default 10 minutes)
and saves the output to a text file.
"""

import subprocess
import signal
import sys
import os
import json
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
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in credentials file: {e}")
        return None, None, None


def run_gnmic_subscribe(
    target: Optional[str] = None,
    timeout: str = "60s",
    encoding: str = "json_ietf",
    path: str = "/",
    output_file: str = "gnmi_subscribe_output.txt",
    duration_seconds: int = 600,  # 10 minutes
    skip_verify: bool = True,
    username: Optional[str] = None,
    password: Optional[str] = None,
    credentials_file: Optional[str] = None,
    sample_interval: str = "10s",
    mode: str = "stream",
    stream_mode: str = "sample",
    port: int = 57344
) -> None:
    """
    Run gnmic subscribe command and save output to a file.
    
    Args:
        target: Target address in format ip:port (optional, can be loaded from credentials)
        timeout: Connection timeout (e.g., "60s")
        encoding: Data encoding format (e.g., "json_ietf", "json", "proto")
        path: gNMI path to subscribe to
        output_file: Output file path for the subscription data
        duration_seconds: How long to run the subscription (default 600s = 10 min)
        skip_verify: Skip TLS certificate verification
        username: Optional username for authentication
        password: Optional password for authentication
        credentials_file: Optional path to JSON file with credentials
        sample_interval: Sample interval for stream mode (e.g., "10s")
        mode: Subscription mode (stream, once, poll)
        stream_mode: Stream subscription mode (sample, on_change, target_defined)
        port: gNMI port (default: 57344, used when host is loaded from credentials)
    """
    
    # Load credentials from file if specified
    if credentials_file:
        file_host, file_user, file_pass = load_credentials(credentials_file)
        # Use host from credentials if target not explicitly provided
        if file_host and not target:
            target = f"{file_host}:{port}"
        if file_user and not username:
            username = file_user
        if file_pass and not password:
            password = file_pass
    
    # Ensure target is set
    if not target:
        print("Error: Target address is required (set in credentials file or via --address)")
        sys.exit(1)
    
    # Build the gnmic command
    cmd = [
        "gnmic",
        "-a", target,
        f"--timeout={timeout}",
        "subscribe",
        "--encoding", encoding,
        "--path", path,
        "--mode", mode,
        "--stream-mode", stream_mode,
        "--sample-interval", sample_interval,
    ]
    
    if skip_verify:
        cmd.append("--skip-verify")
    
    if username:
        cmd.extend(["-u", username])
    
    if password:
        cmd.extend(["-p", password])
    
    print(f"Starting gnmic subscribe...")
    print(f"Target: {target}")
    print(f"Path: {path}")
    print(f"Encoding: {encoding}")
    print(f"Duration: {duration_seconds} seconds ({duration_seconds // 60} minutes)")
    print(f"Output file: {output_file}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    start_time = datetime.now()
    process = None
    
    try:
        # Open output file for writing
        with open(output_file, "w") as f:
            # Write header information
            f.write(f"# gNMIc Subscribe Output\n")
            f.write(f"# Start Time: {start_time.isoformat()}\n")
            f.write(f"# Target: {target}\n")
            f.write(f"# Path: {path}\n")
            f.write(f"# Encoding: {encoding}\n")
            f.write(f"# Duration: {duration_seconds} seconds\n")
            f.write(f"# Command: {' '.join(cmd)}\n")
            f.write("-" * 60 + "\n\n")
            f.flush()
            
            # Start the gnmic process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Set up timeout using alarm signal
            def timeout_handler(signum, frame):
                print(f"\n\nSubscription duration ({duration_seconds}s) reached. Stopping...")
                if process:
                    process.terminate()
            
            # Register the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(duration_seconds)
            
            # Read and write output line by line
            print("Subscription started. Receiving data...")
            line_count = 0
            
            try:
                for line in process.stdout:
                    timestamp = datetime.now().isoformat()
                    f.write(f"[{timestamp}] {line}")
                    f.flush()
                    line_count += 1
                    
                    # Print progress every 100 lines
                    if line_count % 100 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        print(f"  Received {line_count} messages ({elapsed:.0f}s elapsed)...")
                        
            except Exception as e:
                print(f"Error reading output: {e}")
            
            # Cancel the alarm
            signal.alarm(0)
            
            # Wait for process to finish
            process.wait()
            
            # Write footer
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            f.write("\n" + "-" * 60 + "\n")
            f.write(f"# End Time: {end_time.isoformat()}\n")
            f.write(f"# Total Duration: {duration:.2f} seconds\n")
            f.write(f"# Total Messages: {line_count}\n")
            
        print("-" * 60)
        print(f"Subscription completed!")
        print(f"End Time: {end_time.isoformat()}")
        print(f"Total Duration: {duration:.2f} seconds")
        print(f"Total Messages: {line_count}")
        print(f"Output saved to: {os.path.abspath(output_file)}")
        
    except KeyboardInterrupt:
        print("\n\nSubscription interrupted by user (Ctrl+C)")
        if process:
            process.terminate()
            process.wait()
        
        # Write proper footer to the file even on interrupt
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        try:
            with open(output_file, "a") as f:
                f.write("\n" + "-" * 60 + "\n")
                f.write(f"# INTERRUPTED BY USER (Ctrl+C)\n")
                f.write(f"# End Time: {end_time.isoformat()}\n")
                f.write(f"# Total Duration: {duration:.2f} seconds\n")
                f.write(f"# Total Messages: {line_count}\n")
        except Exception:
            pass  # Don't fail on footer write error
        
        print(f"Output saved to: {os.path.abspath(output_file)}")
        sys.exit(0)
        
    except FileNotFoundError:
        print("Error: gnmic command not found. Please install gnmic:")
        print("  brew install gnmic  # macOS")
        print("  or visit: https://gnmic.openconfig.net/install/")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        if process:
            process.terminate()
        sys.exit(1)


def main():
    """Main entry point with configurable parameters."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run gnmic subscribe and save output to file"
    )
    parser.add_argument(
        "-a", "--address",
        default=None,
        help="Target address (ip:port) - defaults to host from credentials file"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=57344,
        help="gNMI port when using host from credentials (default: 57344)"
    )
    parser.add_argument(
        "-t", "--timeout",
        default="60s",
        help="Connection timeout (default: 60s)"
    )
    parser.add_argument(
        "-e", "--encoding",
        default="json_ietf",
        choices=["json", "json_ietf", "proto", "ascii"],
        help="Data encoding (default: json_ietf)"
    )
    parser.add_argument(
        "-p", "--path",
        default="/",
        help="gNMI path to subscribe to"
    )
    parser.add_argument(
        "-o", "--output",
        default="gnmi_subscribe_output.txt",
        help="Output file path (default: gnmi_subscribe_output.txt)"
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=600,
        help="Subscription duration in seconds (default: 600 = 10 min)"
    )
    parser.add_argument(
        "-u", "--username",
        help="Username for authentication"
    )
    parser.add_argument(
        "--password",
        help="Password for authentication"
    )
    parser.add_argument(
        "-c", "--credentials-file",
        default="gnmi_credentials.json",
        help="Path to JSON file with credentials (default: gnmi_credentials.json)"
    )
    parser.add_argument(
        "-i", "--sample-interval",
        default="10s",
        help="Sample interval for stream mode (default: 10s)"
    )
    parser.add_argument(
        "-m", "--mode",
        default="stream",
        choices=["stream", "once", "poll"],
        help="Subscription mode (default: stream)"
    )
    parser.add_argument(
        "-s", "--stream-mode",
        default="sample",
        choices=["sample", "on_change", "target_defined"],
        help="Stream subscription mode (default: sample)"
    )
    parser.add_argument(
        "--no-skip-verify",
        action="store_true",
        help="Do not skip TLS certificate verification"
    )
    
    args = parser.parse_args()
    
    run_gnmic_subscribe(
        target=args.address,
        timeout=args.timeout,
        encoding=args.encoding,
        path=args.path,
        output_file=args.output,
        duration_seconds=args.duration,
        skip_verify=not args.no_skip_verify,
        username=args.username,
        password=args.password,
        credentials_file=args.credentials_file,
        sample_interval=args.sample_interval,
        mode=args.mode,
        stream_mode=args.stream_mode,
        port=args.port
    )


if __name__ == "__main__":
    main()
