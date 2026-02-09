# 📸 MediaSnap Documentation

**Version:** 0.1 (MVP)  
**Status:** Public data only  
**Platform:** Desktop (Python + Tkinter)

---

## 1. Overview

**MediaSnap** is a lightweight desktop tool for **archiving public Instagram media and metadata**.
It allows users to fetch, download, and persist posts from **public Instagram profiles** without requiring authentication.

MediaSnap focuses on:

* Reliability
* Clean architecture
* Local-first data ownership
* Persistence via SQLAlchemy

> MediaSnap is **not a bot**, **not an automation tool**, and **does not bypass private accounts**.

---

## 2. Core Features

### Supported

* ✅ Public Instagram profiles
* ✅ Feed posts (images & carousels)
* ✅ Post metadata persistence
* ✅ Local SQLite database
* ✅ Duplicate detection
* ✅ Desktop GUI

### Not Supported (by design)

* ❌ Private accounts
* ❌ Stories & highlights
* ❌ Login / password handling
* ❌ Likes/comments scraping beyond counts

---

## 3. System Architecture

MediaSnap follows a **layered architecture** to ensure maintainability and extensibility.

```
┌─────────────────────────┐
│        UI Layer         │  (Tkinter + ttkbootstrap)
└─────────────┬───────────┘
              │
┌─────────────▼───────────┐
│     Application Core    │  (Instagram client, logic)
└─────────────┬───────────┘
              │
┌─────────────▼───────────┐
│   Persistence Layer     │  (SQLAlchemy ORM)
└─────────────┬───────────┘
              │
┌─────────────▼───────────┐
│  Filesystem Storage     │  (Media files)
└─────────────────────────┘
```

---

## 4. Technology Stack

### Language

* Python 3.10+

### UI

* `tkinter`
* `ttkbootstrap`

### Networking

* `httpx`

### Parsing

* `orjson` (with fallback to stdlib json)
* `beautifulsoup4`
* `lxml`

### Persistence

* `SQLAlchemy` 2.0+
* SQLite (default)
* `aiosqlite` for async support

### Async

* `asyncio` (stdlib)
* `aiofiles`

### Resilience

* `tenacity` for retry logic

---

## 5. Project Structure

```text
mediasnap/
│
├── app.py                          # Simple entry point
├── requirements.txt
│
├── mediasnap/
│   ├── __init__.py                 # Version info
│   ├── __main__.py                 # Module entry point
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py          # Main GUI window
│   │   ├── async_bridge.py         # Asyncio-Tkinter bridge
│   │   └── styles.py               # UI styling
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scraper.py              # Unified scraper with fallback
│   │   ├── downloader.py           # Media downloader
│   │   ├── app_service.py          # Service orchestration
│   │   ├── rate_limiter.py         # Rate limiting
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── scrapers/
│   │       ├── __init__.py
│   │       ├── html_scraper.py     # HTML parsing strategy
│   │       └── graphql_scraper.py  # GraphQL strategy
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py             # Engine & sessions
│   │   └── repository.py           # Data access layer
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schema.py               # SQLAlchemy ORM models
│   │   └── data_models.py          # In-memory data classes
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py               # Configuration
│       └── logging.py              # Logging setup
│
├── downloads/                      # Media storage
│   └── {username}/
│       └── {shortcode}_{index}.{ext}
│
├── logs/                          # Application logs
│   └── mediasnap.log
│
└── docs/
    └── ARCHITECTURE.md            # This file
```

---

## 6. Data Model

### 6.1 Profile

Represents an Instagram user.

| Field           | Type    | Description              |
| --------------- | ------- | ------------------------ |
| instagram_id    | String  | Instagram user ID (PK)   |
| username        | String  | Instagram username       |
| full_name       | String  | Display name             |
| biography       | Text    | Bio text                 |
| profile_pic_url | String  | Profile image URL        |
| follower_count  | Integer | Follower count           |
| following_count | Integer | Following count          |
| post_count      | Integer | Total posts              |
| is_private      | Boolean | Private account flag     |
| is_verified     | Boolean | Verified badge           |
| fetched_at      | DateTime| Last fetch timestamp     |

**Relationships:**
- One profile has many posts

---

### 6.2 Post

Represents a single Instagram post.

| Field         | Type     | Description              |
| ------------- | -------- | ------------------------ |
| shortcode     | String   | Instagram shortcode (PK) |
| profile_id    | FK       | Owner profile            |
| typename      | String   | Post type (Graph*)       |
| caption       | Text     | Post caption             |
| taken_at      | DateTime | Post timestamp           |
| like_count    | Integer  | Like count               |
| comment_count | Integer  | Comment count            |
| display_url   | String   | Main media URL           |
| is_video      | Boolean  | Video flag               |
| video_url     | String   | Video URL (if video)     |
| is_downloaded | Boolean  | Download status          |
| created_at    | DateTime | DB insertion time        |

**Relationships:**
- One post belongs to one profile
- One post has many media items (for carousels)

---

### 6.3 Media

Represents a downloadable media asset (for carousel posts).

| Field          | Type    | Description           |
| -------------- | ------- | --------------------- |
| id             | Integer | Auto-increment ID (PK)|
| post_shortcode | FK      | Parent post           |
| url            | String  | Media source URL      |
| media_type     | String  | 'image' or 'video'    |
| order          | Integer | Position in carousel  |
| local_path     | String  | Downloaded file path  |
| is_downloaded  | Boolean | Download status       |
| created_at     | DateTime| DB insertion time     |

**Relationships:**
- One media item belongs to one post

---

## 7. Database Strategy

* **SQLite** used by default (`mediasnap.db`)
* **SQLAlchemy ORM** abstracts storage layer
* **Async support** via `aiosqlite`
* **Duplicate prevention** via:
  * Profile: unique `instagram_id`
  * Post: unique `shortcode`
* **Upsert pattern** for profiles (update if exists)
* **Insert-only** for posts (immutable once created)

### Foreign Key Constraints

- Enabled via SQLite pragma
- Cascade delete: deleting profile deletes posts and media

### Session Management

- **Async context manager** for database sessions
- Auto-commit on success, rollback on error
- Session cleanup in finally block

---

## 8. Instagram Data Acquisition

### Multi-Strategy Approach

MediaSnap implements **resilient scraping** with multiple fallback strategies:

#### Strategy 1: HTML Parsing (Primary)

```
GET https://www.instagram.com/{username}/
```

**Extraction:**
- Parse HTML with BeautifulSoup + lxml
- Extract `window._sharedData` from `<script>` tags
- Fallback to `window.__additionalDataLoaded`
- Parse embedded JSON with orjson

**Pros:**
- More stable than API endpoints
- Doesn't require query hashes

**Cons:**
- HTML structure may change
- Requires regex parsing

#### Strategy 2: GraphQL API (Fallback)

```
GET https://www.instagram.com/graphql/query/
```

**Extraction:**
- First fetch profile page to get user ID
- Build GraphQL query with variables
- Use known query hash (must be updated periodically)

**Pros:**
- Structured JSON response
- More data available

**Cons:**
- Query hashes change frequently
- More easily detected/blocked

#### Data Extracted

From both strategies:
- Profile metadata (name, bio, followers, etc.)
- Recent posts (typically 12 posts)
- Post metadata (caption, likes, comments, timestamp)
- Media URLs (images, videos, carousels)

### Limitations

* Returns limited number of posts (12-24 typically)
* Pagination requires additional implementation
* Endpoints may change without notice
* Rate limiting applies

---

## 9. Download Workflow

### Complete Workflow

```
1. User enters username
   ↓
2. MediaSnap fetches profile data (HTML → GraphQL fallback)
   ↓
3. Profile is created/updated in DB
   ↓
4. Posts are parsed into data models
   ↓
5. Check existing posts in DB (by shortcode)
   ↓
6. New posts are saved to DB
   ↓
7. Media items extracted (URLs + carousel items)
   ↓
8. Media downloaded with progress tracking
   ↓
9. Database updated with local paths
   ↓
10. Summary displayed to user
```

### Deduplication Strategy

**Profile Level:**
- Check by `instagram_id` (immutable)
- Update metadata if exists

**Post Level:**
- Check by `shortcode` (unique identifier)
- Skip download if already exists
- Update engagement counts only

**Media Level:**
- Only download for new posts
- Check filesystem to avoid re-downloads

This ensures:
- No wasted downloads
- Safe restarts
- Historical integrity

---

## 10. Persistence Workflow

```
Fetch → Parse → Deduplicate → Persist → Download → Link
```

### Step-by-Step

1. **Fetch:** HTTP request to Instagram
2. **Parse:** Extract JSON, transform to data models
3. **Deduplicate:** Query DB for existing records
4. **Persist:** Upsert profile, insert new posts
5. **Download:** Stream media files to disk
6. **Link:** Update DB with local file paths

### Transactional Safety

- Database operations in async context managers
- Automatic rollback on exceptions
- File downloads use temp files (`.tmp`)
- Rename to final path only on success

---

## 11. User Interface Flow

### Main Screen Components

1. **Header**
   - App name and tagline
   
2. **Input Section**
   - Username entry field
   - Fetch button
   
3. **Progress Section**
   - Progress bar (0-100%)
   - Status label
   
4. **Activity Log**
   - Scrollable text output
   - Shows real-time progress
   - Error messages
   
5. **Footer**
   - Disclaimer text

### UX Principles

* **Blocking during fetch**: Input disabled while fetching
* **Clear status messages**: Each stage communicated
* **Progress tracking**: Real-time updates
* **Minimal controls**: One primary action
* **Accessible feedback**: Log shows details

### Progress Stages

1. **Fetching**: Scraping Instagram
2. **Saving**: Persisting to database
3. **Downloading**: Fetching media files
4. **Complete**: Summary displayed

---

## 12. Error Handling

### Exception Hierarchy

```
MediaSnapError (base)
├── ProfileNotFoundError
├── RateLimitedError
├── ScrapingFailedError
├── DownloadError
└── ParsingError
```

### Handled Cases

* Invalid username → Clear error message
* Network failures → Retry with exponential backoff
* Rate limiting → User-friendly message with advice
* Database errors → Transaction rollback
* Download failures → Continue with others, log failures

### Error Presentation

**To User:**
- Simple, actionable messages
- Suggestions for resolution
- Status in activity log

**To Logs:**
- Full stack traces
- Request/response details
- Debugging information

---

## 13. Performance Considerations

### HTTP Optimization

* **Connection pooling**: httpx AsyncClient reused
* **Keep-alive**: Persistent connections
* **Streaming downloads**: Chunked reading (8KB chunks)
* **Concurrent downloads**: Up to 3 simultaneous

### Database Optimization

* **Batch inserts**: Media items inserted together
* **Indexed columns**: username, shortcode
* **Foreign key constraints**: Enforce referential integrity
* **Lightweight ORM**: SQLAlchemy 2.0 performance improvements

### Memory Management

* **Streaming I/O**: Don't load entire files to memory
* **Async file writes**: Non-blocking disk I/O
* **Session cleanup**: Proper resource disposal
* **Limited concurrency**: Semaphore prevents overload

---

## 14. Legal & Ethical Considerations

MediaSnap:

* ✅ Accesses only **public data**
* ✅ Does not bypass authentication
* ✅ Does not interact with private accounts
* ✅ Implements respectful rate limiting
* ✅ Requires users to respect Instagram's ToS

**User Responsibilities:**

* Do not redistribute content without permission
* Respect copyright and privacy
* Use for personal archival only
* Comply with Instagram's Terms of Service

> **Disclaimer:** MediaSnap is a **personal archiving tool**, not a scraping service. Users are responsible for their usage.

---

## 15. Extensibility Roadmap

### Phase 2: Enhanced Scraping

* **Pagination support**: Fetch all posts, not just recent
* **Reels extraction**: Support for Reels/IGTV
* **Metadata refresh**: Update existing posts
* **Query hash extraction**: Auto-detect GraphQL hashes

### Phase 3: Data Management

* **Export functionality**: CSV / JSON export
* **Media browser**: View downloaded content in UI
* **Profile snapshots**: Track changes over time
* **Search functionality**: Find posts by caption/date

### Phase 4: Distribution

* **Multi-platform packaging**: PyInstaller, py2app
* **Native installers**: macOS .app, Windows .exe, Linux .AppImage
* **Auto-updates**: Check for new versions
* **Plugin system**: Extensible extractors

### Phase 5: Advanced Features

* **Multiple profiles**: Batch fetching
* **Scheduling**: Automatic periodic updates
* **Cloud backup**: Optional sync
* **Alternative UI**: Consider Tauri/Electron

---

## 16. Configuration

All configuration in `mediasnap/utils/config.py`:

### Rate Limiting
```python
REQUEST_DELAY = 3.0          # Seconds between requests
REQUEST_JITTER = 0.6         # Random variance
```

### Downloads
```python
MAX_CONCURRENT_DOWNLOADS = 3  # Simultaneous downloads
DOWNLOAD_CHUNK_SIZE = 8192   # Bytes per chunk
```

### Retries
```python
MAX_RETRIES = 3
RETRY_INITIAL_WAIT = 2.0
RETRY_MAX_WAIT = 30.0
RETRY_MULTIPLIER = 2.0       # Exponential backoff
```

### Timeouts
```python
CONNECT_TIMEOUT = 30.0       # Connection timeout
READ_TIMEOUT = 300.0         # Read timeout (for large files)
```

---

## 17. Implementation Details

### Asyncio-Tkinter Integration

**Challenge:** Tkinter and asyncio have separate event loops

**Solution:** Background thread pattern
```
Main Thread: Tkinter event loop
  ↕ (thread-safe queue)
Background Thread: Asyncio event loop
```

**Implementation:**
- `AsyncExecutor` class manages background thread
- `submit(coro)` queues async tasks
- `Future` objects bridge results back to UI
- UI polls futures with `.after()` (100ms interval)

### Rate Limiting Algorithm

```python
1. Before each request:
   a. Calculate time since last request
   b. Add random jitter (±20%)
   c. Sleep if needed to meet minimum delay
   d. Update last_request_time
2. Execute request
```

### Download Strategy

```python
1. Create temp file (.tmp extension)
2. Stream response in chunks
3. Write chunks asynchronously
4. Track progress (bytes downloaded / total)
5. Verify size matches Content-Length
6. Rename temp to final path
7. Update database
```

### Retry Logic (tenacity)

```python
@retry(
    retry=retry_if_exception_type((NetworkError,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30)
)
async def fetch_data():
    # Network operation
```

**Behavior:**
- Retry on specific exceptions
- Max 3 attempts
- Wait: 2s → 4s → 8s (capped at 30s)

---

## 18. Testing Strategy (Future)

### Unit Tests
- Database operations (CRUD)
- Data model parsing
- Rate limiter logic
- URL generation

### Integration Tests
- HTML parsing with fixtures
- Database session management
- Download pipeline

### End-to-End Tests
- Full fetch workflow (mocked HTTP)
- UI interactions (requires UI testing framework)

---

## 19. Troubleshooting

### Common Issues

**"Profile not found"**
- Cause: Username typo or private account
- Solution: Verify spelling, ensure account is public

**"Rate limited"**
- Cause: Too many requests
- Solution: Wait 10-15 minutes, increase `REQUEST_DELAY`

**"Scraping failed"**
- Cause: Instagram changed HTML structure
- Solution: Check logs, update scraper logic

**UI freezes**
- Cause: Async executor not working
- Solution: Check logs, ensure background thread started

**Missing media**
- Cause: URL expired or download failed
- Solution: Re-run fetch, check network connection

---

## 20. Development Setup

### Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

### Development Tools

**Recommended:**
- Black (code formatting)
- Flake8 (linting)
- mypy (type checking)
- pytest (testing)

### Logging Levels

Development:
```python
setup_logging(level=logging.DEBUG)
```

Production:
```python
setup_logging(level=logging.INFO)
```

---

## 21. File Naming Conventions

### Media Files

**Single media posts:**
```
{shortcode}_0.{ext}
Example: ABC123xyz_0.jpg
```

**Carousel posts:**
```
{shortcode}_{order}.{ext}
Example: ABC123xyz_0.jpg, ABC123xyz_1.mp4, ABC123xyz_2.jpg
```

**Extensions:**
- Images: `.jpg`
- Videos: `.mp4`

### Directory Structure

```
downloads/
├── username1/
│   ├── ABC123_0.jpg
│   ├── DEF456_0.mp4
│   └── GHI789_0.jpg
└── username2/
    └── XYZ999_0.jpg
```

---

## 22. Security Considerations

### Data Privacy

- No passwords stored
- No authentication tokens
- All data local
- No telemetry/tracking

### Network Security

- HTTPS only
- Certificate verification enabled
- No credential transmission

### File System

- Files written to configured directory only
- No arbitrary path injection
- Temp files cleaned up on failure

---

## 23. Known Limitations

### Technical

- **Pagination**: Only fetches initial 12-24 posts
- **Stories**: Not supported
- **Reels**: Limited support
- **Private accounts**: Not accessible
- **High-DPI**: Some UI scaling issues on Retina displays

### Instagram API

- HTML structure changes without notice
- GraphQL query hashes rotate
- Rate limiting thresholds unclear
- No official public API

### Performance

- Sequential scraping (rate limiting)
- SQLite concurrency limits
- Large carousels may be slow

---

## 24. Future Considerations

### Scaling

If MediaSnap needs to scale:
- PostgreSQL for concurrency
- Redis for caching
- Message queue for job distribution
- horizontal scaling of downloaders

### Alternative Approaches

- Official Instagram Graph API (requires approval)
- Third-party scraping APIs (paid)
- Browser automation (Selenium/Playwright)
- Mobile app API endpoints

---

## 25. Contributing Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Document public methods
- Keep functions focused

### Commit Messages

```
feat: Add pagination support
fix: Handle missing caption gracefully
docs: Update installation instructions
refactor: Simplify scraper logic
```

### Pull Request Process

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Update documentation
5. Submit PR with description

---

## 26. Resources

### Dependencies Documentation

- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [httpx](https://www.python-httpx.org/)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [tenacity](https://tenacity.readthedocs.io/)

### Related Projects

- [Instaloader](https://github.com/instaloader/instaloader) - Similar tool with more features
- [Instagram Scraper](https://github.com/arc298/instagram-scraper) - CLI-based scraper

---

## 27. Glossary

**Shortcode**: Instagram's public identifier for posts (e.g., "ABC123xyz")  
**Carousel**: Post with multiple images/videos  
**GraphQL**: Query language used by Instagram's API  
**Upsert**: Database operation that inserts or updates  
**ORM**: Object-Relational Mapping (SQLAlchemy)  
**Async**: Asynchronous programming pattern  
**Rate Limiting**: Controlling request frequency  

---

## 28. Changelog

### Version 0.1.0 (Initial Release)

**Features:**
- HTML and GraphQL scraping
- SQLite persistence
- Async downloads
- Desktop GUI
- Duplicate detection
- Progress tracking
- Error handling
- Logging

**Known Issues:**
- No pagination
- Retina display scaling
- GraphQL hashes may be outdated

---

## 29. License

MIT License (or specify your chosen license)

---

## 30. Contact & Support

For questions, issues, or contributions:
- Check logs: `logs/mediasnap.log`
- Review this documentation
- Open GitHub issue (if applicable)

---

**MediaSnap** - *Capture public media. Keep it local.*

Last Updated: February 9, 2026
