#!/usr/bin/env python3
"""
DB_COMMIT Filter Script
Filters syslog output for %MGBL-CONFIG-6-DB_COMMIT entries and extracts commit IDs.

Outputs a markdown table showing commit IDs and their occurrence count.
"""

import re
import argparse
import json
import os
from datetime import datetime
from collections import Counter, OrderedDict
from typing import List, Dict, Tuple, Optional


def extract_subscription_metadata(log_file: str) -> Optional[Dict[str, str]]:
    """
    Extract subscription metadata from the log file header and footer.
    
    Args:
        log_file: Path to the syslog output log file
        
    Returns:
        Dictionary with start_time, end_time, duration, target, yang_path, or None if not found
    """
    metadata = {}
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if line.startswith('# Start Time:'):
                    metadata['start_time'] = line.split(':', 1)[1].strip()
                elif line.startswith('# End Time:'):
                    metadata['end_time'] = line.split(':', 1)[1].strip()
                elif line.startswith('# Total Duration:'):
                    metadata['duration'] = line.split(':', 1)[1].strip()
                elif line.startswith('# Target:'):
                    metadata['target'] = line.split(':', 1)[1].strip()
                elif line.startswith('# YANG Path:'):
                    metadata['yang_path'] = line.split(':', 1)[1].strip()
    except Exception as e:
        print(f"Warning: Could not extract metadata: {e}")
        return None
    
    return metadata if metadata else None


def extract_commit_ids(log_file: str) -> List[Tuple[str, str, str]]:
    """
    Extract commit IDs from DB_COMMIT entries in log file.
    
    Args:
        log_file: Path to the syslog output log file
        
    Returns:
        List of tuples (timestamp, user, commit_id)
    """
    # Pattern to match DB_COMMIT lines
    # Example: [2025-12-09T16:30:46.936504]           "text": "config[66599]: %MGBL-CONFIG-6-DB_COMMIT : Configuration committed by user 'cisco'. Use 'show configuration commit changes 1000012734' to view the changes.
    
    timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\]'
    db_commit_pattern = r'%MGBL-CONFIG-6-DB_COMMIT\s*:\s*Configuration committed by user \'([^\']+)\'.*commit changes (\d+)'
    
    commits = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if '%MGBL-CONFIG-6-DB_COMMIT' in line:
                    # Extract timestamp
                    ts_match = re.search(timestamp_pattern, line)
                    timestamp = ts_match.group(1) if ts_match else "unknown"
                    
                    # Extract user and commit ID
                    commit_match = re.search(db_commit_pattern, line)
                    if commit_match:
                        user = commit_match.group(1)
                        commit_id = commit_match.group(2)
                        commits.append((timestamp, user, commit_id))
                        
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found")
        return []
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []
    
    return commits


def analyze_commits(commits: List[Tuple[str, str, str]]) -> Dict:
    """
    Analyze commit data for duplicates and statistics.
    
    Args:
        commits: List of (timestamp, user, commit_id) tuples
        
    Returns:
        Dictionary with analysis results
    """
    if not commits:
        return {
            "total_entries": 0,
            "unique_commits": 0,
            "duplicates": {},
            "commit_details": []
        }
    
    # Count occurrences of each commit ID
    commit_ids = [c[2] for c in commits]
    commit_counts = Counter(commit_ids)
    
    # Find duplicates (count > 1)
    duplicates = {cid: count for cid, count in commit_counts.items() if count > 1}
    
    # Build detailed commit info preserving order of first occurrence
    seen_commits = OrderedDict()
    for timestamp, user, commit_id in commits:
        if commit_id not in seen_commits:
            seen_commits[commit_id] = {
                "commit_id": commit_id,
                "first_seen": timestamp,
                "user": user,
                "count": commit_counts[commit_id],
                "is_duplicate": commit_counts[commit_id] > 1
            }
    
    return {
        "total_entries": len(commits),
        "unique_commits": len(commit_counts),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "commit_details": list(seen_commits.values())
    }


def generate_markdown_report(analysis: Dict, output_file: str, log_file: str, metadata: Optional[Dict[str, str]] = None) -> str:
    """
    Generate a markdown report of the commit analysis.
    
    Args:
        analysis: Analysis results dictionary
        output_file: Path to write the markdown report
        log_file: Source log file name for the report
        metadata: Optional subscription metadata (start_time, end_time, duration, etc.)
        
    Returns:
        The generated markdown content
    """
    report_time = datetime.now().isoformat()
    
    md_content = f"""# DB_COMMIT Analysis Report

**Generated:** {report_time}  
**Source File:** `{log_file}`

"""

    # Add subscription metadata if available
    if metadata:
        md_content += """## Subscription Details

| Metric | Value |
|--------|-------|
"""
        if 'target' in metadata:
            md_content += f"| Target Device | {metadata['target']} |\n"
        if 'yang_path' in metadata:
            md_content += f"| YANG Path | {metadata['yang_path']} |\n"
        if 'start_time' in metadata:
            md_content += f"| Start Time | {metadata['start_time']} |\n"
        if 'end_time' in metadata:
            md_content += f"| End Time | {metadata['end_time']} |\n"
        if 'duration' in metadata:
            md_content += f"| Total Duration | {metadata['duration']} |\n"
        
        md_content += "\n"
    
    md_content += f"""## Summary

| Metric | Value |
|--------|-------|
| Total DB_COMMIT Entries | {analysis['total_entries']} |
| Unique Commit IDs | {analysis['unique_commits']} |
| Duplicate Commit IDs | {analysis['duplicate_count']} |

"""
    
    # Duplicates section
    if analysis['duplicates']:
        md_content += """## Duplicate Commit IDs

The following commit IDs appeared more than once in the log:

| Commit ID | Occurrences |
|-----------|-------------|
"""
        for commit_id, count in sorted(analysis['duplicates'].items()):
            md_content += f"| {commit_id} | {count} |\n"
        
        md_content += "\n"
    else:
        md_content += """## Duplicate Commit IDs

✅ **No duplicate commit IDs found.**

"""
    
    # All commits table
    md_content += """## All Commit IDs

| # | Commit ID | First Seen | User | Count | Duplicate |
|---|-----------|------------|------|-------|-----------|
"""
    
    for idx, commit in enumerate(analysis['commit_details'], 1):
        duplicate_marker = "⚠️ Yes" if commit['is_duplicate'] else "No"
        md_content += f"| {idx} | {commit['commit_id']} | {commit['first_seen']} | {commit['user']} | {commit['count']} | {duplicate_marker} |\n"
    
    md_content += f"""
---

## Notes

- **Total DB_COMMIT entries** includes all occurrences of the `%MGBL-CONFIG-6-DB_COMMIT` syslog message
- **Unique Commit IDs** counts each commit ID only once
- **Duplicate Commit IDs** are commit IDs that appear more than once (may indicate re-delivery or multiple subscriptions)
- Timestamps shown are from the gNMI subscription log (local capture time)
"""
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            f.write(md_content)
        print(f"Report saved to: {output_file}")
    except Exception as e:
        print(f"Error writing report: {e}")
    
    return md_content


def main():
    """Main entry point with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Filter syslog output for DB_COMMIT entries and generate a report"
    )
    parser.add_argument(
        "-i", "--input",
        default=None,
        help="Input log file (default: auto-detect latest in results/)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output markdown report file (default: same name as input with .md extension in results/)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output analysis as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed output to console"
    )
    
    args = parser.parse_args()
    
    # Auto-detect input file if not provided
    if args.input is None:
        results_dir = "results"
        if os.path.exists(results_dir):
            # Find the most recent .log file in results/
            log_files = [f for f in os.listdir(results_dir) if f.endswith('.log')]
            if log_files:
                # Sort by modification time, newest first
                log_files.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)
                args.input = os.path.join(results_dir, log_files[0])
                print(f"Auto-detected input file: {args.input}")
            else:
                print("Error: No .log files found in results/ directory")
                return
        else:
            print("Error: results/ directory not found. Run gnmi_subscribe first.")
            return
    
    # Generate output filename if not provided
    if args.output is None:
        # Extract base name from input file and replace .log with _report.md
        input_basename = os.path.basename(args.input)
        if input_basename.endswith('.log'):
            output_basename = input_basename.replace('.log', '_report.md')
        else:
            output_basename = input_basename + '_report.md'
        
        # Put output in results/ directory
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        args.output = os.path.join(results_dir, output_basename)
    
    print(f"DB_COMMIT Filter - Analyzing {args.input}")
    print("=" * 50)
    
    # Extract subscription metadata
    metadata = extract_subscription_metadata(args.input)
    
    # Extract commits
    commits = extract_commit_ids(args.input)
    
    if not commits:
        print("No DB_COMMIT entries found in log file.")
        return
    
    print(f"Found {len(commits)} DB_COMMIT entries")
    
    # Analyze
    analysis = analyze_commits(commits)
    
    print(f"Unique commit IDs: {analysis['unique_commits']}")
    print(f"Duplicate commit IDs: {analysis['duplicate_count']}")
    
    if analysis['duplicates'] and args.verbose:
        print("\nDuplicates:")
        for commit_id, count in sorted(analysis['duplicates'].items()):
            print(f"  {commit_id}: {count} occurrences")
    
    # Generate report
    print(f"\nGenerating report: {args.output}")
    generate_markdown_report(analysis, args.output, args.input, metadata)
    
    # Optional JSON output
    if args.json:
        json_file = args.output.replace('.md', '.json')
        with open(json_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"JSON data saved to: {json_file}")
    
    print("=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
