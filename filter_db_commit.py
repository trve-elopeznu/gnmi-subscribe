#!/usr/bin/env python3
"""
DB_COMMIT Filter Script
Filters syslog output for %MGBL-CONFIG-6-DB_COMMIT entries and extracts commit IDs.

Outputs a markdown table showing commit IDs and their occurrence count.
"""

import re
import argparse
import json
from datetime import datetime
from collections import Counter, OrderedDict
from typing import List, Dict, Tuple


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


def generate_markdown_report(analysis: Dict, output_file: str, log_file: str) -> str:
    """
    Generate a markdown report of the commit analysis.
    
    Args:
        analysis: Analysis results dictionary
        output_file: Path to write the markdown report
        log_file: Source log file name for the report
        
    Returns:
        The generated markdown content
    """
    report_time = datetime.now().isoformat()
    
    md_content = f"""# DB_COMMIT Analysis Report

**Generated:** {report_time}  
**Source File:** `{log_file}`

## Summary

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
        default="syslog_output.log",
        help="Input log file (default: syslog_output.log)"
    )
    parser.add_argument(
        "-o", "--output",
        default="db_commit_report.md",
        help="Output markdown report file (default: db_commit_report.md)"
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
    
    print(f"DB_COMMIT Filter - Analyzing {args.input}")
    print("=" * 50)
    
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
    generate_markdown_report(analysis, args.output, args.input)
    
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
