from nanobot.trading.cards.format import (
    compute_rr,
    format_price,
    render_telegram_card,
    render_whatsapp_card,
    translate_reason,
)


def _payload() -> dict:
    return {
        "decision": "sell",
        "summary": "Gold SELL from structure_break with R:R 2.67",
        "confidence": 0.76,
        "keyReasons": [
            "Structure trend: down",
            "MTF bias: bearish (HTF bearish)",
            "Setup: structure_break R:R 2.67",
        ],
        "gateChain": {"allowed": True},
        "recommendation": {
            "entry": 4349.42,
            "stopLoss": 4358.8748214285715,
            "targets": [4336.813571428571, 4324.207142857142],
        },
    }


def test_format_price_rounds_ugly_floats() -> None:
    assert format_price(4358.8748214285715) == "$4,358.87"


def test_translate_structure_reasons() -> None:
    assert translate_reason("Structure trend: down") == "📉 الاتجاه: هابط"
    assert translate_reason("MTF bias: bearish") == "📊 التحيز: هبوطي"
    assert "كسر هيكل" in translate_reason("Setup: structure_break R:R 2.67")


def test_compute_rr_from_levels() -> None:
    rr = compute_rr(_payload())
    assert rr is not None
    assert 2.6 < rr < 2.8


def test_telegram_card_is_arabic_and_rounded() -> None:
    card = render_telegram_card(_payload())
    assert "توصية" in card
    assert "بيع" in card
    assert "$4,349.42" in card
    assert "$4,358.87" in card
    assert "4358.8748214285715" not in card
    assert "Opening" not in card
    assert "الشارت" not in card
    assert "G1-G7" in card


def test_whatsapp_card_is_arabic() -> None:
    card = render_whatsapp_card(_payload())
    assert "*توصية:" in card
    assert "بيع" in card
    assert "$4,349.42" in card
