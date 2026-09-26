"""Agent API: the public REST / SSE / WebSocket contract over one ``AgentLoop``.

Served as a separate aiohttp application inside the gateway process (see
``docs/designs/mokli-v2/07-agent-gateway.md``). URL prefixes are ``/api/v2``
and ``/ws/v2``. Build it with :func:`mokli.agent_api.app.create_app` or run it
with :class:`mokli.agent_api.app.AgentApiServer`.
"""

from mokli.agent_api.config import AgentApiConfig, load_agent_api_config

__all__ = ["AgentApiConfig", "load_agent_api_config"]
