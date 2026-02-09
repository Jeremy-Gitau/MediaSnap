#!/usr/bin/env python3
"""
View MediaSnap download history
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mediasnap.storage.database import get_async_session
from mediasnap.storage.repository import DownloadHistoryRepository


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_duration(started_at: datetime, completed_at: datetime) -> str:
    """Format duration between two datetimes."""
    duration = completed_at - started_at
    seconds = int(duration.total_seconds())
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


async def view_recent_history(limit: int = 50):
    """View recent download history."""
    async with get_async_session() as session:
        history = await DownloadHistoryRepository.get_recent(session, limit=limit)
        
        if not history:
            print("📭 No download history found")
            return
        
        print(f"\n📊 Recent Downloads (showing {len(history)} records)\n")
        print("=" * 100)
        
        for record in history:
            status = "✅" if record.success else "❌"
            platform_emoji = {
                "instagram": "📸",
                "youtube": "📺",
                "linkedin": "🔗"
            }.get(record.platform, "📦")
            
            duration = format_duration(record.started_at, record.completed_at)
            
            print(f"{status} {platform_emoji} {record.platform.upper()}")
            print(f"   URL: {record.url}")
            if record.username:
                print(f"   User: {record.username}")
            print(f"   Time: {format_datetime(record.started_at)} ({duration})")
            print(f"   Stats: {record.new_items} new, {record.skipped_items} skipped, {record.failed_items} failed")
            
            if record.download_path:
                print(f"   Path: {record.download_path}")
            
            if not record.success and record.error_message:
                print(f"   Error: {record.error_message[:100]}")
            
            print()


async def view_platform_history(platform: str, limit: int = 50):
    """View download history for a specific platform."""
    async with get_async_session() as session:
        history = await DownloadHistoryRepository.get_by_platform(session, platform, limit=limit)
        
        if not history:
            print(f"📭 No {platform} download history found")
            return
        
        print(f"\n📊 {platform.upper()} Downloads (showing {len(history)} records)\n")
        print("=" * 100)
        
        for record in history:
            status = "✅" if record.success else "❌"
            duration = format_duration(record.started_at, record.completed_at)
            
            print(f"{status} {format_datetime(record.started_at)} ({duration})")
            print(f"   URL: {record.url}")
            if record.username:
                print(f"   User: {record.username}")
            print(f"   Stats: {record.new_items} new, {record.skipped_items} skipped, {record.failed_items} failed")
            print()


async def view_stats():
    """View overall download statistics."""
    async with get_async_session() as session:
        stats = await DownloadHistoryRepository.get_stats(session)
        history = await DownloadHistoryRepository.get_recent(session, limit=1000)
        
        # Count by platform
        platform_counts = {}
        for record in history:
            platform_counts[record.platform] = platform_counts.get(record.platform, 0) + 1
        
        # Count successes and failures
        success_count = sum(1 for r in history if r.success)
        failure_count = len(history) - success_count
        
        print("\n📊 Download Statistics\n")
        print("=" * 50)
        print(f"\n📈 Overall Stats:")
        print(f"   Total downloads: {stats['total_downloads']}")
        print(f"   Total items: {stats['total_items']}")
        print(f"   Total failures: {stats['total_failures']}")
        print(f"   Success rate: {(success_count / len(history) * 100):.1f}%" if history else "   Success rate: N/A")
        
        print(f"\n📦 By Platform:")
        for platform, count in sorted(platform_counts.items()):
            emoji = {"instagram": "📸", "youtube": "📺", "linkedin": "🔗"}.get(platform, "📦")
            print(f"   {emoji} {platform.capitalize()}: {count} downloads")
        
        print()


async def search_history(url: str):
    """Search download history by URL."""
    async with get_async_session() as session:
        history = await DownloadHistoryRepository.get_by_url(session, url)
        
        if not history:
            print(f"📭 No download history found for: {url}")
            return
        
        print(f"\n📊 Download History for: {url}\n")
        print("=" * 100)
        
        for record in history:
            status = "✅" if record.success else "❌"
            duration = format_duration(record.started_at, record.completed_at)
            
            print(f"{status} {format_datetime(record.started_at)} ({duration})")
            print(f"   Stats: {record.new_items} new, {record.skipped_items} skipped, {record.failed_items} failed")
            
            if record.download_path:
                print(f"   Path: {record.download_path}")
            
            if not record.success and record.error_message:
                print(f"   Error: {record.error_message}")
            
            print()


def print_usage():
    """Print usage information."""
    print("MediaSnap Download History Viewer")
    print("\nUsage:")
    print("  python scripts/view_history.py [command] [options]")
    print("\nCommands:")
    print("  recent [N]           Show N most recent downloads (default: 50)")
    print("  stats                Show overall download statistics")
    print("  instagram [N]        Show Instagram download history")
    print("  youtube [N]          Show YouTube download history")
    print("  linkedin [N]         Show LinkedIn download history")
    print("  search <URL>         Search for downloads by URL")
    print("\nExamples:")
    print("  python scripts/view_history.py recent 20")
    print("  python scripts/view_history.py stats")
    print("  python scripts/view_history.py instagram")
    print("  python scripts/view_history.py search https://www.youtube.com/@MrBeast")


async def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if not args or args[0] in ["-h", "--help", "help"]:
        print_usage()
        return
    
    command = args[0].lower()
    
    if command == "recent":
        limit = int(args[1]) if len(args) > 1 else 50
        await view_recent_history(limit=limit)
    
    elif command == "stats":
        await view_stats()
    
    elif command in ["instagram", "youtube", "linkedin"]:
        limit = int(args[1]) if len(args) > 1 else 50
        await view_platform_history(command, limit=limit)
    
    elif command == "search":
        if len(args) < 2:
            print("❌ Error: URL required for search")
            print_usage()
            return
        await search_history(args[1])
    
    else:
        print(f"❌ Unknown command: {command}\n")
        print_usage()


if __name__ == "__main__":
    asyncio.run(main())
