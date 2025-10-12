#!/usr/bin/env python3
"""
Codex Client weather tool exposing wttr.in capabilities over MCP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from codex_client import BaseTool, tool

from weather import WeatherAPI


class WeatherTool(BaseTool):
    """Comprehensive weather tool providing current conditions, forecasts, and comparisons."""

    def __init__(self) -> None:
        super().__init__()
        self.recent_queries: List[Dict[str, Any]] = []
        self.query_count = 0
        self.favorite_locations: List[Dict[str, Any]] = []
        self.last_location: Optional[str] = None

    def _record_query(self, location: str, query_type: str) -> None:
        """Record a weather query in the internal history."""
        self.query_count += 1
        self.last_location = location
        self.recent_queries.append(
            {
                "id": self.query_count,
                "location": location,
                "query_type": query_type,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.recent_queries) > 20:
            self.recent_queries = self.recent_queries[-20:]

    @tool()
    async def get_current_weather(self, location: str = "") -> Dict[str, Any]:
        """Get current weather conditions for a specific location."""
        location_key = location or "current location"
        self._record_query(location_key, "current_weather")

        result = await WeatherAPI.get_current_weather(location)
        if result.get("success"):
            loc_info = result.get("location", {})
            print(
                f"\n🌤️ [Weather] Current conditions for {loc_info.get('name', location_key)}: "
                f"{result.get('current', {}).get('condition')} "
                f"{result.get('current', {}).get('temperature_c')}°C\n"
            )
            return {
                "success": True,
                "location": loc_info,
                "current_conditions": result.get("current", {}),
                "observation_time": result.get("timestamp"),
                "history": self.recent_queries,
            }

        error_msg = result.get("error", "Unknown error")
        print(f"\n❌ [Weather] {error_msg} for {location_key}\n")
        return {"success": False, "error": error_msg, "location": location_key}

    @tool()
    async def get_forecast(self, location: str = "", days: int = 3) -> Dict[str, Any]:
        """Get weather forecast for a specific location."""
        location_key = location or "current location"
        days = max(1, min(days, 3))
        self._record_query(location_key, f"forecast_{days}d")

        result = await WeatherAPI.get_forecast(location, days)
        if result.get("success"):
            print(f"\n🌦️ [Weather] {days}-day forecast for {result['location']['name']} retrieved\n")
            return {
                "success": True,
                "location": result.get("location"),
                "forecast": result.get("forecast", []),
                "days_requested": days,
                "history": self.recent_queries,
            }

        error_msg = result.get("error", "Unknown error")
        print(f"\n❌ [Weather] {error_msg} for {location_key}\n")
        return {"success": False, "error": error_msg, "location": location_key, "days_requested": days}

    @tool()
    async def get_weather_summary(self, location: str = "") -> Dict[str, Any]:
        """Get a brief weather summary for a location."""
        location_key = location or "current location"
        self._record_query(location_key, "summary")

        result = await WeatherAPI.get_weather_summary(location)
        if result.get("success"):
            print(f"\n📝 [Weather] Summary for {location_key}: {result.get('summary')}\n")
            return {"success": True, "location": result.get("location"), "summary": result.get("summary")}

        error_msg = result.get("error", "Unknown error")
        print(f"\n❌ [Weather] {error_msg} for {location_key}\n")
        return {"success": False, "error": error_msg, "location": location_key}

    @tool()
    async def compare_weather(self, location1: str, location2: str) -> Dict[str, Any]:
        """Compare current weather conditions between two locations."""
        composite_key = f"{location1} vs {location2}"
        self._record_query(composite_key, "comparison")

        result1 = await self.get_current_weather(location1)
        result2 = await self.get_current_weather(location2)

        if result1.get("success") and result2.get("success"):
            loc1_info = result1.get("location", {})
            loc2_info = result2.get("location", {})
            current1 = result1.get("current_conditions", {})
            current2 = result2.get("current_conditions", {})

            print(f"\n🔄 [Weather] Comparing {loc1_info.get('name')} vs {loc2_info.get('name')}\n")

            temp_diff_c = current1.get("temperature_c", 0) - current2.get("temperature_c", 0)
            humidity_diff = current1.get("humidity", 0) - current2.get("humidity", 0)

            return {
                "success": True,
                "location1": {"info": loc1_info, "conditions": current1},
                "location2": {"info": loc2_info, "conditions": current2},
                "comparison": {
                    "temperature_difference_c": temp_diff_c,
                    "humidity_difference": humidity_diff,
                    "warmer_location": loc1_info.get("name") if temp_diff_c > 0 else loc2_info.get("name"),
                    "more_humid_location": loc1_info.get("name") if humidity_diff > 0 else loc2_info.get("name"),
                },
                "history": self.recent_queries,
            }

        errors = []
        if not result1.get("success"):
            errors.append(f"{location1}: {result1.get('error', 'Unknown error')}")
        if not result2.get("success"):
            errors.append(f"{location2}: {result2.get('error', 'Unknown error')}")

        return {"success": False, "errors": errors, "history": self.recent_queries}

    @tool()
    async def add_favorite_location(self, location: str, nickname: str = "") -> Dict[str, Any]:
        """Add a location to the favorites list."""
        existing = next(
            (fav for fav in self.favorite_locations if fav["location"].lower() == location.lower()),
            None,
        )
        if existing:
            return {
                "success": False,
                "message": f"{location} is already in favorites as {existing.get('nickname', location)}",
                "favorites": self.favorite_locations,
            }

        entry = {
            "location": location,
            "nickname": nickname or location,
            "added_at": datetime.now().isoformat(),
        }
        self.favorite_locations.append(entry)
        print(f"\n⭐ [Weather] Added favorite location: {entry['nickname']} ({location})\n")
        return {"success": True, "favorites": self.favorite_locations}

    @tool()
    async def list_favorites(self) -> Dict[str, Any]:
        """List all favorite locations."""
        return {"success": True, "favorites": self.favorite_locations}

    @tool()
    async def show_history(self) -> Dict[str, Any]:
        """Show recent weather queries."""
        return {"success": True, "history": self.recent_queries}
