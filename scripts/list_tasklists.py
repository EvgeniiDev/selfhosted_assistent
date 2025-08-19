#!/usr/bin/env python3
"""List Google Tasks tasklists (id + title).

Reads env vars from `main.env` if present (simple KEY=VALUE parsing) so the
GOOGLE_OAUTH_TOKEN stored there will be used.

Usage:
  python scripts/list_tasklists.py

"""
import os
import sys
from pathlib import Path
from pprint import pprint

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load main.env if exists (simple loader)
env_path = PROJECT_ROOT / 'main.env'
if env_path.exists():
    print(f"Loading env from {env_path}")
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # Only set if not already set in environment
        if key not in os.environ:
            os.environ[key] = val

try:
    from google_calendar_client import GoogleCalendarClient
except Exception as e:
    print(f"Failed to import GoogleCalendarClient: {e}")
    raise


def main():
    try:
        client = GoogleCalendarClient()
    except Exception as e:
        print(f"Failed to initialize GoogleCalendarClient: {e}")
        raise

    try:
        lists = client.tasks_service.tasklists().list(maxResults=500).execute()
        items = lists.get('items', []) if lists else []
        if not items:
            print('No tasklists returned by the API.')
            return

        print(f"Found {len(items)} tasklist(s):")
        for it in items:
            tid = it.get('id')
            title = it.get('title')
            print(f"- id: {tid} | title: {title}")

    except Exception as e:
        print(f"Error while listing tasklists: {e}")
        # If googleapiclient HttpError, print repr for details
        try:
            from googleapiclient.errors import HttpError
            if isinstance(e, HttpError):
                print(repr(e))
        except Exception:
            pass


if __name__ == '__main__':
    main()
