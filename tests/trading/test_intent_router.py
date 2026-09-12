from nanobot.trading.intent_router import route_intent


def test_route_price_query() -> None:
    intent = route_intent("What is the gold price?")
    assert intent.kind == "price_query"


def test_route_recommendation_arabic() -> None:
    intent = route_intent("اعطني توصية على الذهب")
    assert intent.kind == "recommendation"


def test_route_general_chat() -> None:
    intent = route_intent("hello there")
    assert intent.kind == "general_chat"
