"""HTML scraping strategy for Instagram profiles."""

import json
import random
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from mediasnap.core.exceptions import ParsingError, ProfileNotFoundError, RateLimitedError, ScrapingFailedError
from mediasnap.core.rate_limiter import get_rate_limiter
from mediasnap.models.data_models import MediaItem, PostData, ProfileData
from mediasnap.utils.config import (
    CONNECT_TIMEOUT,
    INSTAGRAM_BASE_URL,
    READ_TIMEOUT,
    USER_AGENTS,
)
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class HTMLScraper:
    """Scrapes Instagram profiles by parsing HTML."""
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Create HTTP client on context entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT),
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client on context exit."""
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> dict:
        """Generate request headers with random user agent."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def fetch_profile(self, username: str) -> ProfileData:
        """
        Fetch profile data by parsing HTML.
        
        Args:
            username: Instagram username
        
        Returns:
            ProfileData object
        
        Raises:
            ProfileNotFoundError: If profile doesn't exist
            RateLimitedError: If rate limited
            ScrapingFailedError: If scraping fails
        """
        if not self.client:
            raise ScrapingFailedError("HTTPScraper must be used as context manager")
        
        url = f"{INSTAGRAM_BASE_URL}/{username}/"
        
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        logger.info(f"Fetching profile HTML: {username}")
        
        try:
            response = await self.client.get(url, headers=self._get_headers())
            
            # Check response status
            if response.status_code == 404:
                raise ProfileNotFoundError(f"Profile not found: {username}")
            elif response.status_code == 429:
                raise RateLimitedError("Rate limited by Instagram")
            elif response.status_code != 200:
                raise ScrapingFailedError(f"HTTP {response.status_code}: {response.text[:100]}")
            
            # Parse HTML
            html = response.text
            
            # Log HTML structure for debugging
            if len(html) < 1000:
                logger.warning(f"Received very short HTML response ({len(html)} bytes). Possible redirect or error page.")
                logger.debug(f"Full response: {html}")
            
            # Check for common Instagram blocking patterns
            if "login" in html.lower() and len(html) < 10000:
                logger.warning("Response may be a login redirect. Instagram might be requiring authentication.")
            
            profile_data = self._parse_html(html, username)
            
            logger.info(f"Successfully scraped profile: {username} ({len(profile_data.posts)} posts)")
            return profile_data
            
        except (ProfileNotFoundError, RateLimitedError, ScrapingFailedError):
            raise
        except httpx.TimeoutException as e:
            raise ScrapingFailedError(f"Request timeout: {str(e)}")
        except httpx.HTTPError as e:
            raise ScrapingFailedError(f"HTTP error: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping {username}")
            raise ScrapingFailedError(f"Unexpected error: {str(e)}")
    
    def _parse_html(self, html: str, username: str) -> ProfileData:
        """
        Parse profile data from HTML.
        
        Args:
            html: HTML content
            username: Instagram username
        
        Returns:
            ProfileData object
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Try multiple extraction methods in order of likelihood
        data = (self._extract_shared_data(soup) or 
                self._extract_json_from_scripts(soup) or
                self._extract_additional_data(soup))
        
        if not data:
            logger.error("Could not extract data from HTML. Instagram may have changed their structure.")
            # Log what script tags we found for debugging
            script_tags = soup.find_all("script")
            logger.debug(f"Found {len(script_tags)} script tags in HTML")
            for i, script in enumerate(script_tags[:5]):  # Log first 5
                if script.string:
                    preview = script.string[:100].replace('\n', ' ')
                    logger.debug(f"Script {i}: {preview}...")
            
            raise ParsingError(
                "Could not extract data from HTML. Instagram's page structure may have changed. "
                "The profile may be private, require login, or Instagram is blocking automated access."
            )
        
        # Parse profile and posts
        try:
            return self._parse_profile_data(data, username)
        except Exception as e:
            logger.exception("Failed to parse profile data")
            raise ParsingError(f"Failed to parse data: {str(e)}")
    
    def _extract_shared_data(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract window._sharedData from script tags."""
        scripts = soup.find_all("script", string=re.compile(r"window\._sharedData"))
        
        for script in scripts:
            text = script.string
            match = re.search(r"window\._sharedData\s*=\s*({.+?});\s*$", text, re.MULTILINE)
            if match:
                try:
                    data = json.loads(match.group(1))
                    logger.debug("Extracted window._sharedData")
                    return data
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse _sharedData: {e}")
                    continue
        
        return None
    
    def _extract_additional_data(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract window.__additionalDataLoaded from script tags."""
        scripts = soup.find_all("script", string=re.compile(r"window\.__additionalDataLoaded"))
        
        for script in scripts:
            text = script.string
            matches = re.findall(r"window\.__additionalDataLoaded\([^,]+,\s*({.+?})\);", text, re.DOTALL)
            if matches:
                try:
                    data = json.loads(matches[0])
                    logger.debug("Extracted window.__additionalDataLoaded")
                    return data
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse __additionalDataLoaded: {e}")
                    continue
        
        return None
    
    def _extract_json_from_scripts(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract JSON data from script tags with type='application/json'."""
        # Instagram sometimes embeds data in JSON script tags
        json_scripts = soup.find_all("script", type="application/json")
        
        for script in json_scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                # Look for Instagram data patterns
                if isinstance(data, dict):
                    # Check for common Instagram data structures
                    if any(key in data for key in ['require', 'graphql', 'data', 'entry_data']):
                        logger.debug("Extracted JSON from application/json script tag")
                        return data
            except json.JSONDecodeError:
                continue
        
        # Try to find any script with large JSON objects
        all_scripts = soup.find_all("script")
        for script in all_scripts:
            if not script.string or len(script.string) < 100:
                continue
            
            # Look for JSON patterns in script content
            json_pattern = r'(\{["\']require["\'].*?\}|\{["\']graphql["\'].*?\})'
            matches = re.findall(json_pattern, script.string, re.DOTALL)
            
            for match in matches:
                try:
                    # Try to find a valid JSON object
                    data = json.loads(match)
                    logger.debug("Extracted JSON from script content")
                    return data
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _parse_profile_data(self, data: dict, username: str) -> ProfileData:
        """Parse JSON data into ProfileData object."""
        
        # Navigate data structure (structure may vary)
        user_data = None
        
        # Try different paths to user data
        if "entry_data" in data:
            entry_data = data["entry_data"]
            if "ProfilePage" in entry_data and entry_data["ProfilePage"]:
                graphql = entry_data["ProfilePage"][0].get("graphql", {})
                user_data = graphql.get("user", {})
        
        if not user_data and "graphql" in data:
            user_data = data["graphql"].get("user", {})
        
        if not user_data:
            raise ParsingError("Could not find user data in JSON")
        
        # Extract profile information
        profile = ProfileData(
            instagram_id=user_data.get("id", ""),
            username=user_data.get("username", username),
            full_name=user_data.get("full_name"),
            biography=user_data.get("biography"),
            profile_pic_url=user_data.get("profile_pic_url_hd") or user_data.get("profile_pic_url"),
            follower_count=user_data.get("edge_followed_by", {}).get("count"),
            following_count=user_data.get("edge_follow", {}).get("count"),
            post_count=user_data.get("edge_owner_to_timeline_media", {}).get("count"),
            is_private=user_data.get("is_private", False),
            is_verified=user_data.get("is_verified", False),
        )
        
        # Extract posts
        timeline_media = user_data.get("edge_owner_to_timeline_media", {})
        edges = timeline_media.get("edges", [])
        
        for edge in edges:
            node = edge.get("node", {})
            post = self._parse_post_node(node)
            if post:
                profile.posts.append(post)
        
        return profile
    
    def _parse_post_node(self, node: dict) -> Optional[PostData]:
        """Parse a post node into PostData object."""
        try:
            shortcode = node.get("shortcode")
            if not shortcode:
                return None
            
            # Extract caption
            caption = None
            edge_caption = node.get("edge_media_to_caption", {})
            if edge_caption.get("edges"):
                caption = edge_caption["edges"][0].get("node", {}).get("text")
            
            # Extract timestamp
            taken_at = None
            timestamp = node.get("taken_at_timestamp")
            if timestamp:
                taken_at = datetime.fromtimestamp(timestamp)
            
            # Create post data
            post = PostData(
                shortcode=shortcode,
                typename=node.get("__typename", ""),
                caption=caption,
                taken_at=taken_at,
                like_count=node.get("edge_liked_by", {}).get("count"),
                comment_count=node.get("edge_media_to_comment", {}).get("count"),
                display_url=node.get("display_url"),
                is_video=node.get("is_video", False),
                video_url=node.get("video_url"),
            )
            
            # Handle carousel posts (multiple media items)
            if node.get("__typename") == "GraphSidecar":
                carousel_media = node.get("edge_sidecar_to_children", {}).get("edges", [])
                for idx, carousel_edge in enumerate(carousel_media):
                    carousel_node = carousel_edge.get("node", {})
                    media_item = MediaItem(
                        url=carousel_node.get("video_url") or carousel_node.get("display_url", ""),
                        media_type="video" if carousel_node.get("is_video") else "image",
                        order=idx,
                    )
                    post.media_items.append(media_item)
            
            return post
            
        except Exception as e:
            logger.warning(f"Failed to parse post node: {str(e)}")
            return None
