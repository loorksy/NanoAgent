from nanobot.trading.i18n import artifact_title, gate_label, label_map, tr


def test_tr_arabic_price_header() -> None:
    assert "XAUUSD" in tr("price.header", "ar")


def test_tr_english_price_header() -> None:
    assert tr("price.header", "en") == "XAUUSD live quote"


def test_artifact_title_formal_arabic() -> None:
    assert artifact_title("chart_snapshot", "ar") == "لقطة الرسم البياني"


def test_gate_label_hides_internal_id() -> None:
    assert gate_label("G1", "ar") == "درع الأخبار والأحداث"
    assert "G1" not in gate_label("G1", "en")


def test_card_labels_formal_arabic() -> None:
    labels = label_map("card", "ar")
    assert labels["entry"] == "نقطة الدخول"
    assert labels["stop"] == "وقف الخسارة"
    assert "G1" not in labels["gates_pass"]
