#!/usr/bin/env python3
"""
Windsurf Analytics Exporter

This script fetches user emails from the Windsurf User Page Analytics API
and then queries the Cascade Analytics API for each user to export their
analytics data to a CSV file.

Requirements:
- Service key with "Teams Read-only" permissions
- requests library (pip install requests)
"""

import requests
import csv
import json
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import argparse
from pathlib import Path


class WindsurfAnalyticsExporter:
    def __init__(self, service_key: str, base_url: str = "https://server.codeium.com/api/v1"):
        """
        Initialize the exporter with service key and base URL.
        
        Args:
            service_key: Service key with "Teams Read-only" permissions
            base_url: Base URL for the Windsurf API
        """
        self.service_key = service_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def get_user_emails(self, group_name: Optional[str] = None, 
                       start_timestamp: Optional[str] = None,
                       end_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch user emails and basic info from User Page Analytics API.
        
        Args:
            group_name: Optional group name to filter users
            start_timestamp: Start time in RFC 3339 format
            end_timestamp: End time in RFC 3339 format
            
        Returns:
            List of user dictionaries containing email, name, etc.
        """
        url = f"{self.base_url}/UserPageAnalytics"
        
        payload = {
            "service_key": self.service_key
        }
        
        if group_name:
            payload["group_name"] = group_name
        if start_timestamp:
            payload["start_timestamp"] = start_timestamp
        if end_timestamp:
            payload["end_timestamp"] = end_timestamp
            
        print(f"Fetching user emails from {url}...")
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            users = data.get("userTableStats", [])
            
            print(f"Found {len(users)} users")
            return users
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user emails: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            sys.exit(1)

    def get_cascade_analytics(self, emails: List[str], 
                            start_timestamp: Optional[str] = None,
                            end_timestamp: Optional[str] = None,
                            ide_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch Cascade Analytics for specified emails.
        
        Args:
            emails: List of email addresses to query
            start_timestamp: Start time in RFC 3339 format
            end_timestamp: End time in RFC 3339 format
            ide_types: List of IDE types to filter by
            
        Returns:
            Dictionary containing analytics results
        """
        url = f"{self.base_url}/CascadeAnalytics"
        
        payload = {
            "service_key": self.service_key,
            "emails": emails,
            "query_requests": [
                {"cascade_lines": {}},
                {"cascade_runs": {}},
                {"cascade_tool_usage": {}}
            ]
        }
        
        if start_timestamp:
            payload["start_timestamp"] = start_timestamp
        if end_timestamp:
            payload["end_timestamp"] = end_timestamp
        if ide_types:
            payload["ide_types"] = ide_types
            
        print(f"Fetching cascade analytics for {len(emails)} emails...")
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching cascade analytics: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return {}

    def process_analytics_data(self, users: List[Dict[str, Any]], 
                             analytics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and combine user data with analytics data.
        
        Args:
            users: List of user dictionaries from User Page Analytics
            analytics_data: Analytics data from Cascade Analytics API
            
        Returns:
            List of processed records for CSV export
        """
        processed_records = []
        
        # Extract analytics results
        query_results = analytics_data.get("queryResults", [])
        
        cascade_lines_data = {}
        cascade_runs_data = {}
        cascade_tool_usage_data = {}
        
        # Parse query results
        for result in query_results:
            if "cascadeLines" in result:
                lines_data = result["cascadeLines"].get("cascadeLines", [])
                for line_stat in lines_data:
                    # Group by day for aggregation
                    day = line_stat.get("day", "")
                    if day not in cascade_lines_data:
                        cascade_lines_data[day] = {
                            "lines_suggested": 0,
                            "lines_accepted": 0
                        }
                    cascade_lines_data[day]["lines_suggested"] += int(line_stat.get("linesSuggested", 0))
                    cascade_lines_data[day]["lines_accepted"] += int(line_stat.get("linesAccepted", 0))
            
            elif "cascadeRuns" in result:
                runs_data = result["cascadeRuns"].get("cascadeRuns", [])
                for run_stat in runs_data:
                    day = run_stat.get("day", "")
                    if day not in cascade_runs_data:
                        cascade_runs_data[day] = {
                            "messages_sent": 0,
                            "prompts_used": 0,
                            "unique_cascades": set()
                        }
                    cascade_runs_data[day]["messages_sent"] += int(run_stat.get("messagesSent", 0))
                    cascade_runs_data[day]["prompts_used"] += int(run_stat.get("promptsUsed", 0))
                    cascade_id = run_stat.get("cascadeId", "")
                    if cascade_id:
                        cascade_runs_data[day]["unique_cascades"].add(cascade_id)
            
            elif "cascadeToolUsage" in result:
                tool_data = result["cascadeToolUsage"].get("cascadeToolUsage", [])
                for tool_stat in tool_data:
                    tool = tool_stat.get("tool", "")
                    count = int(tool_stat.get("count", 0))
                    cascade_tool_usage_data[tool] = cascade_tool_usage_data.get(tool, 0) + count

        # Create records for each user
        for user in users:
            email = user.get("email", "")
            
            # Aggregate totals across all days
            total_lines_suggested = sum(data["lines_suggested"] for data in cascade_lines_data.values())
            total_lines_accepted = sum(data["lines_accepted"] for data in cascade_lines_data.values())
            total_messages_sent = sum(data["messages_sent"] for data in cascade_runs_data.values())
            total_prompts_used = sum(data["prompts_used"] for data in cascade_runs_data.values())
            
            # Count unique cascades across all days
            all_unique_cascades = set()
            for data in cascade_runs_data.values():
                all_unique_cascades.update(data["unique_cascades"])
            total_unique_cascades = len(all_unique_cascades)
            
            record = {
                "email": email,
                "name": user.get("name", ""),
                "active_days": user.get("activeDays", 0),
                "last_update_time": user.get("lastUpdateTime", ""),
                "last_autocomplete_usage": user.get("lastAutocompleteUsageTime", ""),
                "last_chat_usage": user.get("lastChatUsageTime", ""),
                "last_command_usage": user.get("lastCommandUsageTime", ""),
                "total_lines_suggested": total_lines_suggested,
                "total_lines_accepted": total_lines_accepted,
                "acceptance_rate": f"{(total_lines_accepted / total_lines_suggested * 100):.2f}%" if total_lines_suggested > 0 else "0%",
                "total_messages_sent": total_messages_sent,
                "total_prompts_used_cents": total_prompts_used,
                "total_prompts_used_credits": f"{total_prompts_used / 100:.2f}",
                "total_unique_cascades": total_unique_cascades,
            }
            
            # Add tool usage data
            for tool, count in cascade_tool_usage_data.items():
                record[f"tool_{tool.lower()}"] = count
            
            processed_records.append(record)
        
        return processed_records

    def export_to_csv(self, records: List[Dict[str, Any]], filename: str):
        """
        Export processed records to CSV file.
        
        Args:
            records: List of processed record dictionaries
            filename: Output CSV filename
        """
        if not records:
            print("No records to export")
            return
        
        # Get all unique fieldnames from all records
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        print(f"Exporting {len(records)} records to {filename}...")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
            
            print(f"Successfully exported to {filename}")
            
        except Exception as e:
            print(f"Error writing CSV file: {e}")
            sys.exit(1)

    def run_export(self, output_file: str = "windsurf_analytics.csv",
                  group_name: Optional[str] = None,
                  start_timestamp: Optional[str] = None,
                  end_timestamp: Optional[str] = None,
                  ide_types: Optional[List[str]] = None,
                  batch_size: int = 10):
        """
        Run the complete export process.
        
        Args:
            output_file: Output CSV filename
            group_name: Optional group name to filter users
            start_timestamp: Start time in RFC 3339 format
            end_timestamp: End time in RFC 3339 format
            ide_types: List of IDE types to filter by
            batch_size: Number of emails to process in each batch
        """
        print("Starting Windsurf Analytics Export...")
        
        # Step 1: Get user emails
        users = self.get_user_emails(group_name, start_timestamp, end_timestamp)
        
        if not users:
            print("No users found")
            return
        
        # Step 2: Process users individually (one request per email)
        all_records = []
        emails = [user["email"] for user in users if user.get("email")]
        
        total = len(emails)
        for idx, email in enumerate(emails, start=1):
            print(f"Processing {idx}/{total}: {email}")
            
            # Get analytics for this single email
            analytics_data = self.get_cascade_analytics(
                [email], start_timestamp, end_timestamp, ide_types
            )
            
            # Process the single user's data
            user_obj = next((u for u in users if u.get("email") == email), None)
            if not user_obj:
                continue
            records = self.process_analytics_data([user_obj], analytics_data)
            all_records.extend(records)
        
        # Step 3: Export to CSV
        self.export_to_csv(all_records, output_file)
        
        print(f"Export completed! Total users processed: {len(all_records)}")


def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    # Handle both 'KEY=value' and 'export KEY=value' formats
                    if line.startswith('export '):
                        line = line[7:]  # Remove 'export ' prefix
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value


def main():
    # Load .env file first
    load_env_file()
    
    parser = argparse.ArgumentParser(description="Export Windsurf user analytics to CSV")
    parser.add_argument("--service-key", 
                       default=os.getenv('WINDSURF_SERVICE_KEY'),
                       help="Service key with Teams Read-only permissions (default: from WINDSURF_SERVICE_KEY env var)")
    parser.add_argument("--output", default="windsurf_analytics.csv",
                       help="Output CSV filename (default: windsurf_analytics.csv)")
    parser.add_argument("--group-name", 
                       help="Filter users by group name")
    parser.add_argument("--start-timestamp",
                       help="Start time in RFC 3339 format (e.g., 2024-01-01T00:00:00Z)")
    parser.add_argument("--end-timestamp",
                       help="End time in RFC 3339 format (e.g., 2024-12-31T23:59:59Z)")
    parser.add_argument("--ide-types", nargs="+", choices=["editor", "jetbrains"],
                       help="Filter by IDE types")
    parser.add_argument("--batch-size", type=int, default=10,
                       help="Number of emails to process per batch (default: 10)")
    parser.add_argument("--base-url", default="https://server.codeium.com/api/v1",
                       help="Base URL for Windsurf API")
    
    args = parser.parse_args()
    
    # Check if service key is available
    if not args.service_key:
        print("Error: Service key is required. Either:")
        print("  1. Set WINDSURF_SERVICE_KEY in your .env file, or")
        print("  2. Use --service-key argument")
        sys.exit(1)
    
    # Create exporter instance
    exporter = WindsurfAnalyticsExporter(args.service_key, args.base_url)
    
    # Run the export
    exporter.run_export(
        output_file=args.output,
        group_name=args.group_name,
        start_timestamp=args.start_timestamp,
        end_timestamp=args.end_timestamp,
        ide_types=args.ide_types,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
