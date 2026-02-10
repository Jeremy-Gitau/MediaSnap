"""LinkedIn profile and company page downloader."""

import asyncio
import re
from pathlib import Path
from typing import Any, Callable, Optional

import aiofiles
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mediasnap.utils.config import DOWNLOAD_DIR, SESSION_DIR
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class LinkedInDownloader:
    """
    LinkedIn content downloader for profiles and company pages.
    Uses linkedin-api library for authenticated access.
    """

    def __init__(self):
        """Initialize LinkedIn downloader."""
        self.downloaded_count = 0
        self.failed_count = 0
        self.failed_items = []
        self.linkedin_api = None

    def _is_linkedin_url(self, url: str) -> bool:
        """
        Check if URL is a LinkedIn profile or company page URL.

        Args:
            url: URL to check

        Returns:
            True if LinkedIn URL
        """
        patterns = [
            r"(?:https?://)?(?:www\.)?linkedin\.com/in/",  # Profile
            r"(?:https?://)?(?:www\.)?linkedin\.com/company/",  # Company
        ]
        return any(re.search(pattern, url) for pattern in patterns)

    def _extract_profile_id(self, url: str) -> tuple[str, str]:
        """
        Extract profile ID or company name from LinkedIn URL.

        Args:
            url: LinkedIn URL

        Returns:
            Tuple of (type, identifier) where type is 'profile' or 'company'
        """
        # Profile pattern
        profile_match = re.search(
            r"linkedin\.com/in/([^/\?]+)", url, re.IGNORECASE
        )
        if profile_match:
            return ("profile", profile_match.group(1))

        # Company pattern
        company_match = re.search(
            r"linkedin\.com/company/([^/\?]+)", url, re.IGNORECASE
        )
        if company_match:
            return ("company", company_match.group(1))

        return ("unknown", "")

    async def _authenticate(self) -> bool:
        """
        Authenticate with LinkedIn using encrypted saved session.

        Returns:
            True if authentication successful
        """
        try:
            from linkedin_api import Linkedin
            import pickle

            # Check for encrypted session file
            session_file = SESSION_DIR / "linkedin_session.enc"
            old_session = SESSION_DIR / "linkedin_session.pkl"

            if session_file.exists():
                logger.info(f"Loading encrypted LinkedIn session from {session_file}")
                # Load and decrypt session
                from mediasnap.core.auth_helpers import _decrypt_data
                
                with open(session_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = _decrypt_data(encrypted_data)
                session_data = pickle.loads(decrypted_data)
                
                self.linkedin_api = Linkedin(
                    session_data["username"], session_data["password"]
                )
                return True
            elif old_session.exists():
                # Backward compatibility with old unencrypted format
                logger.warning(f"Loading legacy unencrypted session from {old_session}")
                with open(old_session, "rb") as f:
                    session_data = pickle.load(f)
                    self.linkedin_api = Linkedin(
                        session_data["username"], session_data["password"]
                    )
                return True
            else:
                logger.error(
                    f"No LinkedIn session found at {session_file}. "
                    "Please login via the UI or run scripts/linkedin_login.py first"
                )
                return False

        except ImportError:
            logger.error(
                "linkedin-api not installed. Run: pip install linkedin-api"
            )
            return False
        except Exception as e:
            logger.error(f"LinkedIn authentication failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def _download_file(self, url: str, filepath: Path) -> bool:
        """
        Download a file from URL with retry logic.

        Args:
            url: URL to download
            filepath: Destination file path

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()

                filepath.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(filepath, "wb") as f:
                    await f.write(response.content)

                logger.debug(f"Downloaded: {filepath.name}")
                return True

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            raise

    async def download_profile(
        self,
        profile_url: str,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> dict[str, Any]:
        """
        Download all content from a LinkedIn profile or company page.

        Args:
            profile_url: LinkedIn profile or company page URL
            progress_callback: Optional callback(stage, current, total, message)

        Returns:
            Dictionary with download results
        """

        def report_progress(stage: str, current: int, total: int, message: str):
            if progress_callback:
                progress_callback(stage, current, total, message)

        try:
            report_progress("Initialize", 0, 100, "Starting LinkedIn download...")

            # Authenticate
            if not await self._authenticate():
                raise Exception(
                    "LinkedIn authentication required. Run scripts/linkedin_login.py"
                )

            report_progress("Authenticate", 10, 100, "Authenticated with LinkedIn")

            # Extract profile/company identifier
            content_type, identifier = self._extract_profile_id(profile_url)

            if content_type == "unknown":
                raise Exception(f"Could not parse LinkedIn URL: {profile_url}")

            logger.info(
                f"Downloading LinkedIn {content_type}: {identifier}"
            )

            # Create download directory
            download_base = DOWNLOAD_DIR / "linkedin" / identifier
            download_base.mkdir(parents=True, exist_ok=True)

            # Fetch content based on type
            if content_type == "profile":
                result = await self._download_profile_content(
                    identifier, download_base, report_progress
                )
            else:  # company
                result = await self._download_company_content(
                    identifier, download_base, report_progress
                )

            report_progress("Complete", 100, 100, "Download complete!")

            return {
                "identifier": identifier,
                "type": content_type,
                "downloaded": self.downloaded_count,
                "failed": self.failed_count,
                "failed_items": self.failed_items,
                "download_path": str(download_base),
                "success": True,
            }

        except Exception as e:
            logger.exception(f"LinkedIn download failed: {e}")
            return {
                "identifier": profile_url,
                "type": "unknown",
                "downloaded": 0,
                "failed": 0,
                "failed_items": [str(e)],
                "download_path": "",
                "success": False,
            }

    async def _download_profile_content(
        self,
        profile_id: str,
        download_dir: Path,
        progress_callback: Callable[[str, int, int, str], None],
    ) -> dict[str, Any]:
        """
        Download profile posts, articles, and media.

        Args:
            profile_id: LinkedIn profile identifier
            download_dir: Download directory
            progress_callback: Progress callback

        Returns:
            Download results dictionary
        """
        progress_callback("Fetch Profile", 20, 100, f"Fetching profile: {profile_id}")

        try:
            # Get profile information
            profile = self.linkedin_api.get_profile(profile_id)

            # Save profile info
            info_file = download_dir / "profile_info.json"
            import json

            async with aiofiles.open(info_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(profile, indent=2, ensure_ascii=False))

            logger.info(f"Saved profile info: {info_file}")

            progress_callback("Fetch Posts", 30, 100, "Fetching posts...")

            # Get profile posts/updates
            posts = self.linkedin_api.get_profile_posts(profile_id, post_count=100)

            progress_callback(
                "Download Posts", 40, 100, f"Found {len(posts)} posts"
            )

            # Create folders
            posts_dir = download_dir / "posts"
            articles_dir = download_dir / "articles"
            videos_dir = download_dir / "videos"
            documents_dir = download_dir / "documents"

            posts_dir.mkdir(exist_ok=True)
            articles_dir.mkdir(exist_ok=True)
            videos_dir.mkdir(exist_ok=True)
            documents_dir.mkdir(exist_ok=True)

            # Process each post
            total_items = len(posts)
            for idx, post in enumerate(posts):
                try:
                    await self._process_linkedin_post(
                        post,
                        posts_dir,
                        articles_dir,
                        videos_dir,
                        documents_dir,
                    )
                    self.downloaded_count += 1

                    # Update progress
                    progress = 40 + int((idx + 1) / total_items * 60)
                    progress_callback(
                        "Download",
                        progress,
                        100,
                        f"Processing post {idx + 1}/{total_items}",
                    )

                except Exception as e:
                    logger.error(f"Failed to process post: {e}")
                    self.failed_count += 1
                    self.failed_items.append(f"Post {idx}: {str(e)}")

            return {
                "profile": profile,
                "posts_count": len(posts),
            }

        except Exception as e:
            logger.exception(f"Profile download failed: {e}")
            raise

    async def _download_company_content(
        self,
        company_id: str,
        download_dir: Path,
        progress_callback: Callable[[str, int, int, str], None],
    ) -> dict[str, Any]:
        """
        Download company page posts and updates.

        Args:
            company_id: LinkedIn company identifier
            download_dir: Download directory
            progress_callback: Progress callback

        Returns:
            Download results dictionary
        """
        progress_callback("Fetch Company", 20, 100, f"Fetching company: {company_id}")

        try:
            # Get company information
            company = self.linkedin_api.get_company(company_id)

            # Save company info
            info_file = download_dir / "company_info.json"
            import json

            async with aiofiles.open(info_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(company, indent=2, ensure_ascii=False))

            logger.info(f"Saved company info: {info_file}")

            progress_callback("Fetch Updates", 30, 100, "Fetching company updates...")

            # Get company updates
            updates = self.linkedin_api.get_company_updates(
                company_id, max_results=100
            )

            progress_callback(
                "Download Updates", 40, 100, f"Found {len(updates)} updates"
            )

            # Create folders
            posts_dir = download_dir / "posts"
            videos_dir = download_dir / "videos"
            documents_dir = download_dir / "documents"

            posts_dir.mkdir(exist_ok=True)
            videos_dir.mkdir(exist_ok=True)
            documents_dir.mkdir(exist_ok=True)

            # Process each update
            total_items = len(updates)
            for idx, update in enumerate(updates):
                try:
                    await self._process_linkedin_post(
                        update,
                        posts_dir,
                        None,
                        videos_dir,
                        documents_dir,
                    )
                    self.downloaded_count += 1

                    # Update progress
                    progress = 40 + int((idx + 1) / total_items * 60)
                    progress_callback(
                        "Download",
                        progress,
                        100,
                        f"Processing update {idx + 1}/{total_items}",
                    )

                except Exception as e:
                    logger.error(f"Failed to process update: {e}")
                    self.failed_count += 1
                    self.failed_items.append(f"Update {idx}: {str(e)}")

            return {
                "company": company,
                "updates_count": len(updates),
            }

        except Exception as e:
            logger.exception(f"Company download failed: {e}")
            raise

    async def _process_linkedin_post(
        self,
        post: dict[str, Any],
        posts_dir: Path,
        articles_dir: Optional[Path],
        videos_dir: Path,
        documents_dir: Path,
    ) -> None:
        """
        Process a single LinkedIn post and download its content.

        Args:
            post: Post data dictionary
            posts_dir: Posts directory
            articles_dir: Articles directory (None for company posts)
            videos_dir: Videos directory
            documents_dir: Documents directory
        """
        import json

        # Get post ID
        post_id = post.get("urn", "").split(":")[-1] or str(hash(str(post)))[:8]

        # Save post JSON
        post_file = posts_dir / f"{post_id}.json"
        async with aiofiles.open(post_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(post, indent=2, ensure_ascii=False))

        # Check for article content
        if articles_dir and post.get("article"):
            article_data = post["article"]
            article_file = articles_dir / f"{post_id}_article.json"
            async with aiofiles.open(article_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(article_data, indent=2, ensure_ascii=False))
            logger.info(f"Saved article: {article_file.name}")

        # Check for media content
        if post.get("content"):
            content = post["content"]

            # Images
            if content.get("images"):
                for idx, img_url in enumerate(content["images"]):
                    try:
                        img_file = posts_dir / f"{post_id}_img_{idx}.jpg"
                        await self._download_file(img_url, img_file)
                    except Exception as e:
                        logger.error(f"Failed to download image: {e}")

            # Videos
            if content.get("video"):
                try:
                    video_url = content["video"].get("url")
                    if video_url:
                        video_file = videos_dir / f"{post_id}.mp4"
                        await self._download_file(video_url, video_file)
                        logger.info(f"Downloaded video: {video_file.name}")
                except Exception as e:
                    logger.error(f"Failed to download video: {e}")

            # Documents (PDFs, etc.)
            if content.get("document"):
                try:
                    doc_url = content["document"].get("url")
                    doc_title = content["document"].get("title", "document")
                    if doc_url:
                        # Determine file extension
                        ext = Path(doc_url).suffix or ".pdf"
                        doc_file = documents_dir / f"{post_id}_{doc_title}{ext}"
                        await self._download_file(doc_url, doc_file)
                        logger.info(f"Downloaded document: {doc_file.name}")
                except Exception as e:
                    logger.error(f"Failed to download document: {e}")
