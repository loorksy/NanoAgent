"""Quality-check chain (wire ids G1–G20; operator copy uses i18n names)."""

from mokli.trading.gates.build_gates import build_gates
from mokli.trading.gates.chain import run_gate_chain

__all__ = ["build_gates", "run_gate_chain"]
