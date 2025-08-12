# Windsurf Analytics Exporter

This Python script fetches user emails from the Windsurf User Page Analytics API and queries the Cascade Analytics API for each user to export their analytics data to a CSV file.

## Features

- Fetches all users from your Windsurf team/organization
- Queries Cascade Analytics for each user including:
  - Lines suggested/accepted with acceptance rates
  - Message counts and credit usage
  - Tool usage statistics
  - User activity data
- Exports comprehensive analytics to CSV format
- Processes one request per email (per-user isolation)
- Configurable time ranges and filtering options

## Requirements

- Python 3.6+
- Service key with "Teams Read-only" permissions from Windsurf
- `requests` library

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Get your service key:
   - Log into your Windsurf Teams/Enterprise account
   - Navigate to API settings
   - Create a service key with "Teams Read-only" permissions

3. (Recommended) Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Add your service key to a local .env file (loaded automatically):
   ```bash
   echo 'WINDSURF_SERVICE_KEY="your_key_here"' > .env
   # or
   echo 'export WINDSURF_SERVICE_KEY="your_key_here"' > .env
   ```

## Usage

### Basic Usage

```bash
# With .env configured (no need to pass the key)
python windsurf_analytics_exporter.py
```

### Advanced Usage

```bash
# Export specific group with time range
python windsurf_analytics_exporter.py \
  --group-name "engineering_team" \
  --start-timestamp "2024-01-01T00:00:00Z" \
  --end-timestamp "2024-12-31T23:59:59Z" \
  --output "team_analytics_2024.csv"

# Filter by IDE type
python windsurf_analytics_exporter.py \
  --ide-types editor jetbrains \
  --output "ide_analytics.csv"
```

### Command Line Options

- `--service-key`: Your Windsurf service key (default: reads `WINDSURF_SERVICE_KEY` from `.env`)
- `--output`: Output CSV filename (default: windsurf_analytics.csv)
- `--group-name`: Filter users by group name
- `--start-timestamp`: Start time in RFC 3339 format (e.g., 2024-01-01T00:00:00Z)
- `--end-timestamp`: End time in RFC 3339 format (e.g., 2024-12-31T23:59:59Z)
- `--ide-types`: Filter by IDE types (editor, jetbrains)
- `--batch-size`: Legacy option; currently not used in per-email mode
- `--base-url`: Custom API base URL (default: https://server.codeium.com/api/v1)

## Output CSV Columns

The exported CSV includes the following columns for each user:

### User Information
- `email`: User's email address
- `name`: User's display name
- `active_days`: Total active days in the queried timeframe
- `last_update_time`: Timestamp of user's last activity
- `last_autocomplete_usage`: Last Tab/Autocomplete usage
- `last_chat_usage`: Last Cascade usage
- `last_command_usage`: Last command usage

### Cascade Analytics
- `total_lines_suggested`: Total lines suggested by Cascade
- `total_lines_accepted`: Total lines accepted by user
- `acceptance_rate`: Percentage of lines accepted
- `total_messages_sent`: Total messages sent in Cascade
- `total_prompts_used_cents`: Total credits used (in cents)
- `total_prompts_used_credits`: Total credits used (in dollars)
- `total_unique_cascades`: Number of unique conversations

### Tool Usage
- `tool_code_action`: Code edit tool usage count
- `tool_view_file`: View file tool usage count
- `tool_run_command`: Run command tool usage count
- `tool_find`: Find tool usage count
- `tool_grep_search`: Grep search tool usage count
- `tool_view_file_outline`: View file outline tool usage count
- `tool_mquery`: Riptide tool usage count
- `tool_list_directory`: List directory tool usage count
- `tool_mcp_tool`: MCP tool usage count
- `tool_propose_code`: Propose code tool usage count
- `tool_search_web`: Search web tool usage count
- `tool_memory`: Memory tool usage count
- `tool_proxy_web_server`: Browser preview tool usage count
- `tool_deploy_web_app`: Deploy web app tool usage count

## API Rate Limits

The script now performs one API request per email (per-user). If you hit rate limits, consider:
- Narrowing the time range (`--start-timestamp`, `--end-timestamp`)
- Filtering to a specific group with `--group-name`
- Running during off-peak hours

## Error Handling

The script includes comprehensive error handling for:
- API authentication errors
- Network connectivity issues
- Invalid timestamps or parameters
- Missing or malformed data

## Security Notes

- Never commit your service key to version control
- Store your service key as an environment variable:
  ```bash
  export WINDSURF_SERVICE_KEY="your_key_here"
  python windsurf_analytics_exporter.py --service-key "$WINDSURF_SERVICE_KEY"
  ```

## Example Output

The script will output progress information:

```
Starting Windsurf Analytics Export...
Fetching user emails from https://server.codeium.com/api/v1/UserPageAnalytics...
Found 25 users
Processing 1/25: alice@windsurf.com
Processing 2/25: bob@windsurf.com
Processing 3/25: charlie@windsurf.com
...
Exporting 25 records to windsurf_analytics.csv...
Successfully exported to windsurf_analytics.csv
Export completed! Total users processed: 25
```
