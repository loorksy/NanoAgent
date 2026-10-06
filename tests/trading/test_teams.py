from mokli.trading.teams.runtime import load_preset, topological_layers


def test_load_gold_debate_desk_preset():
    preset = load_preset("gold_debate_desk")
    assert preset.name == "gold_debate_desk"
    assert len(preset.agents) >= 3
    layers = topological_layers(preset.tasks)
    assert len(layers) == 3
    assert [task.id for task in layers[0]] == ["task-technical"]
    assert {task.id for task in layers[1]} == {"task-bull", "task-bear"}
    assert [task.id for task in layers[2]] == ["task-risk"]
