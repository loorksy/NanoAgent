from nanobot.trading.i18n import artifact_title, label_map, tr


def test_tr_arabic_price_header() -> None:
    assert "XAUUSD" in tr("price.header", "ar")


def test_tr_english_price_header() -> None:
    assert tr("price.header", "en") == "XAUUSD live quote"


def test_artifact_title_formal_arabic() -> None:
    assert artifact_title("chart_snapshot", "ar") == "لقطة الرسم البياني"


def test_card_labels_formal_arabic() -> None:
    labels = label_map("card", "ar")
    assert labels["entry"] == "نقطة الدخول"
    assert labels["stop"] == "وقف الخسارة"
