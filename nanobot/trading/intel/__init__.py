"""Free-tier gold intelligence engines (FEATURE-01 … FEATURE-10)."""

from nanobot.trading.intel.calendar_scraper import fetch_economic_calendar
from nanobot.trading.intel.dtw_matcher import match_pattern
from nanobot.trading.intel.intermarket import intermarket_snapshot
from nanobot.trading.intel.local_sentiment import classify_sentiment
from nanobot.trading.intel.postmortem import PostMortemLog
from nanobot.trading.intel.regex_emergency import scan_emergency
from nanobot.trading.intel.rss_aggregator import fetch_rss_headlines
from nanobot.trading.intel.telegram_scraper import TelegramHeadlineSource
from nanobot.trading.intel.tickets import TicketStore
from nanobot.trading.intel.vector_playbook import VectorPlaybook
from nanobot.trading.intel.vip_tracker import fetch_vip_statements

__all__ = [
    "TelegramHeadlineSource",
    "fetch_rss_headlines",
    "fetch_vip_statements",
    "fetch_economic_calendar",
    "scan_emergency",
    "VectorPlaybook",
    "match_pattern",
    "PostMortemLog",
    "TicketStore",
    "classify_sentiment",
    "intermarket_snapshot",
]
