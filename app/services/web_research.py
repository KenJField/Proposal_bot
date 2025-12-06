"""Web research service using Google Search API."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..core.config import settings
from ..core.redis_client import cache_get, cache_set


class WebResearchService:
    """Service for performing web research using Google Search API."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def search_company_info(self, company_name: str) -> Dict[str, Any]:
        """Search for company information."""
        cache_key = f"company_info:{company_name}"

        # Check cache first
        cached_result = await cache_get(cache_key)
        if cached_result:
            return eval(cached_result)  # In production, use JSON

        try:
            query = f'"{company_name}" company overview industry employees website'
            results = await self._perform_search(query, num_results=10)

            # Extract company information
            company_info = {
                "name": company_name,
                "industry": self._extract_industry(results),
                "website": self._extract_website(results),
                "description": self._extract_description(results),
                "headquarters": self._extract_headquarters(results),
                "employee_count": self._extract_employee_count(results),
                "founded_year": self._extract_founded_year(results),
                "sources": [r.get("link", "") for r in results[:3]],
                "last_updated": "2024-01-01T00:00:00Z"
            }

            # Cache for 24 hours
            await cache_set(cache_key, str(company_info), ttl_seconds=86400)

            return company_info

        except Exception as e:
            self.logger.error(f"Company research failed for {company_name}: {e}")
            return {"name": company_name, "error": str(e)}

    async def search_industry_trends(self, industry: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Search for industry trends and insights."""
        search_topic = f"{topic} " if topic else ""
        query = f'"{industry}" industry trends {search_topic}2024 market research'

        cache_key = f"industry_trends:{industry}:{topic or 'general'}"

        # Check cache
        cached_result = await cache_get(cache_key)
        if cached_result:
            return eval(cached_result)

        try:
            results = await self._perform_search(query, num_results=15)

            trends = {
                "industry": industry,
                "topic": topic,
                "trends": self._extract_trends(results),
                "key_insights": self._extract_insights(results),
                "sources": [r.get("link", "") for r in results[:5]],
                "last_updated": "2024-01-01T00:00:00Z"
            }

            # Cache for 12 hours
            await cache_set(cache_key, str(trends), ttl_seconds=43200)

            return trends

        except Exception as e:
            self.logger.error(f"Industry trends search failed for {industry}: {e}")
            return {"industry": industry, "error": str(e)}

    async def search_competitive_landscape(self, company_name: str, industry: str) -> Dict[str, Any]:
        """Search for competitive landscape information."""
        query = f'"{company_name}" competitors in {industry} market share'

        cache_key = f"competitors:{company_name}"

        # Check cache
        cached_result = await cache_get(cache_key)
        if cached_result:
            return eval(cached_result)

        try:
            results = await self._perform_search(query, num_results=10)

            competitors = {
                "company": company_name,
                "industry": industry,
                "direct_competitors": self._extract_competitors(results),
                "market_position": self._extract_market_position(results),
                "competitive_advantages": self._extract_competitive_advantages(results),
                "sources": [r.get("link", "") for r in results[:3]],
                "last_updated": "2024-01-01T00:00:00Z"
            }

            # Cache for 24 hours
            await cache_set(cache_key, str(competitors), ttl_seconds=86400)

            return competitors

        except Exception as e:
            self.logger.error(f"Competitive landscape search failed for {company_name}: {e}")
            return {"company": company_name, "error": str(e)}

    async def _perform_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Perform Google search and return results."""
        try:
            # Use Google Custom Search API if configured
            if settings.google_search_api_key and settings.google_search_engine_id:
                return await self._google_custom_search_api(query, num_results)
            else:
                # Fallback to mock data when API not configured
                return self._mock_search_results(query, num_results)

        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {e}")
            return self._mock_search_results(query, num_results)

    async def _google_custom_search_api(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Use Google Custom Search API."""
        try:
            from googleapiclient.discovery import build

            service = build("customsearch", "v1", developerKey=settings.google_search_api_key)

            # Perform search
            result = service.cse().list(
                q=query,
                cx=settings.google_search_engine_id,
                num=min(num_results, 10)  # API limit is 10 per request
            ).execute()

            results = []
            if "items" in result:
                for item in result["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "display_link": item.get("displayLink", "")
                    })

            return results

        except Exception as e:
            self.logger.error(f"Google Custom Search API failed: {e}")
            raise

    def _mock_search_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Return mock search results when API is not available."""
        return [
            {
                "title": f"Mock Result {i+1} for: {query}",
                "link": f"https://example.com/result{i+1}",
                "snippet": f"This is mock search result {i+1} for the query: {query}. In production, this would be real search data.",
                "display_link": f"example.com"
            }
            for i in range(min(num_results, 5))
        ]

    def _extract_industry(self, results: List[Dict[str, Any]]) -> str:
        """Extract industry information from search results."""
        # Simple keyword extraction - in production would use NLP
        industries = ["technology", "healthcare", "finance", "retail", "manufacturing", "consulting"]

        for result in results:
            text = result.get("snippet", "").lower()
            for industry in industries:
                if industry in text:
                    return industry.title()

        return "Unknown"

    def _extract_website(self, results: List[Dict[str, Any]]) -> Optional[str]:
        """Extract company website from search results."""
        for result in results:
            link = result.get("link", "")
            if "linkedin.com/company" not in link and "wikipedia.org" not in link:
                return link
        return None

    def _extract_description(self, results: List[Dict[str, Any]]) -> str:
        """Extract company description from search results."""
        for result in results[:3]:  # Check first 3 results
            snippet = result.get("snippet", "")
            if len(snippet) > 50:  # Decent length description
                return snippet[:300] + "..." if len(snippet) > 300 else snippet
        return "Company description not found"

    def _extract_headquarters(self, results: List[Dict[str, Any]]) -> Optional[str]:
        """Extract headquarters location."""
        for result in results:
            snippet = result.get("snippet", "").lower()
            # Look for location patterns
            if "headquartered in" in snippet or "based in" in snippet:
                return snippet.split("headquartered in")[-1].split("based in")[-1].split(".")[0].strip().title()
        return None

    def _extract_employee_count(self, results: List[Dict[str, Any]]) -> Optional[str]:
        """Extract employee count information."""
        for result in results:
            snippet = result.get("snippet", "").lower()
            if "employees" in snippet:
                return snippet.split("employees")[0].split()[-1] + " employees"
        return None

    def _extract_founded_year(self, results: List[Dict[str, Any]]) -> Optional[int]:
        """Extract founding year."""
        for result in results:
            snippet = result.get("snippet", "").lower()
            if "founded in" in snippet or "established in" in snippet:
                try:
                    year_text = snippet.split("founded in")[-1].split("established in")[-1].split()[0]
                    year = int(year_text)
                    if 1800 <= year <= 2024:
                        return year
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_trends(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract industry trends from search results."""
        trends = []
        trend_keywords = ["trend", "growing", "increasing", "emerging", "shifting"]

        for result in results:
            snippet = result.get("snippet", "")
            for keyword in trend_keywords:
                if keyword in snippet.lower():
                    # Extract sentence containing the trend
                    sentences = snippet.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower() and len(sentence.strip()) > 20:
                            trends.append(sentence.strip())
                            break
                    break

            if len(trends) >= 5:  # Limit to 5 trends
                break

        return trends[:5] if trends else ["Market trends analysis requires API configuration"]

    def _extract_insights(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract key insights from search results."""
        insights = []

        for result in results[:5]:
            snippet = result.get("snippet", "")
            if len(snippet) > 100:  # Substantial content
                insights.append(snippet[:200] + "...")

        return insights[:3] if insights else ["Industry insights require API configuration"]

    def _extract_competitors(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract competitor names from search results."""
        competitors = []

        for result in results:
            snippet = result.get("snippet", "")
            # Look for competitor mentions
            if "competitor" in snippet.lower() or "competes with" in snippet.lower():
                # Extract potential company names (simplified)
                words = snippet.split()
                for word in words:
                    if len(word) > 3 and word[0].isupper():
                        competitors.append(word.strip(",."))

        return list(set(competitors))[:5] if competitors else ["Competitor analysis requires API configuration"]

    def _extract_market_position(self, results: List[Dict[str, Any]]) -> str:
        """Extract market position information."""
        for result in results:
            snippet = result.get("snippet", "").lower()
            if "market leader" in snippet or "market share" in snippet:
                return "Market Leader"
            elif "emerging" in snippet or "growing" in snippet:
                return "Emerging Player"
            elif "established" in snippet:
                return "Established Player"

        return "Market Position Unknown"

    def _extract_competitive_advantages(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract competitive advantages."""
        advantages = []

        for result in results:
            snippet = result.get("snippet", "").lower()
            if "advantage" in snippet or "strength" in snippet or "unique" in snippet:
                advantages.append(snippet.split(".")[0].strip().capitalize())

        return advantages[:3] if advantages else ["Competitive advantages require API configuration"]


# Global web research service instance
web_research_service = WebResearchService()
