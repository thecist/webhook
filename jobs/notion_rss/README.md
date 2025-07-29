<!-- Documentation on what this job does -->
# Notion RSS Job

This job syncs RSS/Atom feeds into Notion databases, allowing you to aggregate and manage feed content directly in Notion.

## Overview

- **Fetches RSS/Atom feeds** from a list of subscribed sources in a Notion database.
- **Creates or updates pages** in a target Notion database for each feed entry.
- **Detects content changes** using hashes and only updates pages if the content has changed.
- **Supports rich content**: Markdown, HTML, code blocks, and more are converted for Notion compatibility.

## How It Works

1. Reads a list of RSS sources from the "origin" Notion database.
2. For each source, fetches and parses the feed.
3. For each feed entry:
   - If the entry is new, creates a new page in the "view" Notion database.
   - If the entry exists and content has changed, updates the corresponding Notion page.
   - Skips entries with no changes.
4. Uses configurable property names and statuses for maximum flexibility.

## Configuration

All configuration is managed via environment variables and the job's config section.

### Environment Variables

Set these in `jobs/notion_rss/.env` (see `.env.example`):

```sh
NOTION_RSS_NOTION_TOKEN=your_notion_integration_token NOTION_RSS_ORIGIN_DATABASE_ID=your_origin_database_id NOTION_RSS_VIEW_DATABASE_ID=your_view_database_id
```


### Config Fields

Edit `configs.toml` or use the CLI to set:


- `origin_name_title`: Property name for the feed's name in the origin database.
- `origin_url_title`: Property name for the feed's URL in the origin database.
- `origin_status_title`: Property name for the subscription status.
- `origin_status_subscribed`: Value indicating a feed is subscribed.
- `view_*_title`: Property names for the view database (name, description, status, pub_date, id, source, hash, href).
- `view_status_not_read`: Status value for unread feeds.

See [`settings.py`](settings.py) for all available config options.

## Usage

### Run Manually

#### Testing
```sh
python -m jobs.notion_rss
```

#### CLI
```sh
python -m cli run-job notion_rss
```

### As a Scheduled Job

Enable and schedule via the main CLI:
```sh
python -m cli enable notion_rss
python -m cli set notion_rss.cron="0 * * * *"
python -m cli setup-scheduler
```

### As an API Job

Trigger via HTTP:

```sh
POST /run/notion_rss
```

## Requirements

- Python 3.11+
- See `requirements.txt` for dependencies.

## Development

- Edit `job.py` for main logic.
- Use `__main__.py` for local testing.
- Update `.env.example` if you add new environment variables.
- Add or update config fields in `settings.py` and `defaults.toml`.

## Notes
- Only feeds marked as "Subscribed" in the origin database are processed.
- Content is hashed to detect changes and avoid unnecessary updates.
- Supports a wide range of code and content formats.

---
For advanced configuration or troubleshooting, see the main project README.