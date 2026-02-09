"""GraphQL scraping strategy for Instagram profiles."""

import json
import random
import re
from datetime import datetime
from typing import Optional

import httpx

from mediasnap.core.exceptions import ParsingError, ProfileNotFoundError, RateLimitedError, ScrapingFailedError
from mediasnap.core.rate_limiter import get_rate_limiter
from mediasnap.models.data_models import MediaItem, PostData, ProfileData
from mediasnap.utils.config import (
    CONNECT_TIMEOUT,
    INSTAGRAM_BASE_URL,
    INSTAGRAM_GRAPHQL_URL,
    READ_TIMEOUT,
    USER_AGENTS,
)
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


class GraphQLScraper:
    """Scrapes Instagram profiles using GraphQL API."""
    
    # Known query hashes (these may need updating)
    QUERY_HASHES = {
        "profile": "69cba40317214236af40e7efa697781d",  # Example hash - may be outdated
    }
    
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
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest",
            "X-IG-App-ID": "936619743392459",  # Instagram web app ID
            "Origin": INSTAGRAM_BASE_URL,
            "Connection": "keep-alive",
        }
    
    async def fetch_profile(self, username: str) -> ProfileData:
        """
        Fetch profile data using GraphQL.
        
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
            raise ScrapingFailedError("GraphQLScraper must be used as context manager")
        
        logger.info(f"Fetching profile via GraphQL: {username}")
        
        try:
            # First, get user ID
            user_id = await self._get_user_id(username)
            
            # Then fetch profile data
            profile_data = await self._fetch_profile_data(username, user_id)
            
            logger.info(f"Successfully scraped profile via GraphQL: {username} ({len(profile_data.posts)} posts)")
            return profile_data
            
        except (ProfileNotFoundError, RateLimitedError, ScrapingFailedError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in GraphQL scraper for {username}")
            raise ScrapingFailedError(f"GraphQL error: {str(e)}")
    
    async def _get_user_id(self, username: str) -> str:
        """
        Get Instagram user ID from username.
        
        This makes a request to the profile page to extract the user ID.
        """
        url = f"{INSTAGRAM_BASE_URL}/{username}/?__a=1&__d=dis"
        
        await self.rate_limiter.wait()
        
        try:
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                raise ProfileNotFoundError(f"Profile not found: {username}")
            elif response.status_code == 429:
                raise RateLimitedError("Rate limited by Instagram")
            elif response.status_code not in (200, 201):
                logger.warning(f"Unexpected status code {response.status_code} for {url}")
                logger.debug(f"Response preview: {response.text[:500]}")
                raise ScrapingFailedError(f"HTTP {response.status_code}")
            
            # Try to parse JSON response
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}")
                raise ParsingError(f"Invalid JSON response from Instagram")
            
            # Try to extract user ID from various possible locations
            user_id = None
            if "graphql" in data:
                user_id = data["graphql"].get("user", {}).get("id")
            elif "user" in data:
                user_id = data["user"].get("id")
            elif "data" in data and isinstance(data["data"], dict):
                user_data = data["data"].get("user")
                if user_data:
                    user_id = user_data.get("id")
            
            if not user_id:
                logger.warning(f"Could not find user ID in response. Keys: {list(data.keys())}")
                raise ParsingError("Could not extract user ID from response. Instagram API may have changed.")
            
            return user_id
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProfileNotFoundError(f"Profile not found: {username}")
            raise ScrapingFailedError(f"HTTP error: {str(e)}")
    
    async def _fetch_profile_data(self, username: str, user_id: str) -> ProfileData:
        """
        Fetch profile data using GraphQL query.
        
        Note: This is a simplified implementation. Instagram's GraphQL endpoint
        requires proper query hashes that change frequently. This serves as a
        fallback that may need updates.
        """
        # Build GraphQL query variables
        variables = {
            "id": user_id,
            "first": 12,  # Number of posts to fetch
        }
        
        # Get query hash (this may need to be extracted from Instagram's JS)
        query_hash = self.QUERY_HASHES["profile"]
        
        params = {
            "query_hash": query_hash,
            "variables": json.dumps(variables),
        }
        
        await self.rate_limiter.wait()
        
        try:
            response = await self.client.get(
                INSTAGRAM_GRAPHQL_URL,
                params=params,
                headers=self._get_headers()
            )
            
            if response.status_code == 404:
                raise ProfileNotFoundError(f"Profile not found: {username}")
            elif response.status_code == 429:
                raise RateLimitedError("Rate limited by Instagram")
            elif response.status_code != 200:
                raise ScrapingFailedError(f"GraphQL HTTP {response.status_code}")
            
            data = response.json()
            
            # Parse GraphQL response
            return self._parse_graphql_response(data, username)
            
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON response: {str(e)}")
    
    def _parse_graphql_response(self, data: dict, username: str) -> ProfileData:
        """Parse GraphQL response into ProfileData object."""
        
        try:
            # Navigate GraphQL response structure
            if "data" not in data:
                raise ParsingError("No data in GraphQL response")
            
            user_data = data["data"].get("user")
            if not user_data:
                raise ParsingError("No user data in GraphQL response")
            
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
            
        except Exception as e:
            logger.exception("Failed to parse GraphQL response")
            raise ParsingError(f"GraphQL parsing error: {str(e)}")
    
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
            
            # Handle carousel posts
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
