from nanobot.trading.teams.runtime import load_preset, topological_layers


def test_load_gold_debate_desk_preset():
    preset = load_preset("gold_debate_desk")
    assert preset.name == "gold_debate_desk"
    assert len(preset.agents) >= 3
    layers = topological_layers(preset.tasks)
    assert len(layers) == 2
    assert len(layers[0]) == 2
