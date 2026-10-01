from mokli.agent.tools.context import RequestContext
from mokli.security.secret_store import SecretStore
from mokli.trading.permissions.model import Mt5Permissions
from mokli.trading.permissions.store import PermissionStore, set_permission_store_for_tests
from mokli.trading.prompt_facts import trading_prompt_facts


def test_facts_report_permission_level_and_scope(tmp_path):
    store = PermissionStore(SecretStore(tmp_path / "s.enc"))
    set_permission_store_for_tests(store)
    store.save(
        Mt5Permissions(level="execute", can_open=True, max_lot_per_order=0.2, granted_at=1, granted_by="t"),
        who="t",
        now_s=1.0,
    )
    facts = trading_prompt_facts(RequestContext(channel="websocket", chat_id="c", session_key="websocket:c"))
    assert facts["mt5_permission_level"] == "execute"
    assert "open" in facts["mt5_execute_scope"]
    assert "max_lot_per_order=0.2" in facts["mt5_execute_scope"]
    assert facts["channel"] == "websocket"
    assert facts["execution_mode"] in {"paper", "live"}
    assert facts["instrument"] == "analysis symbol is XAUUSD"
    assert "OANDA" in facts["market_data"]
    assert "MetaAPI" in facts["market_data"]
    assert "MT5 terminal" not in facts["market_data"]
    assert "mt5_market" in facts["market_data"]
