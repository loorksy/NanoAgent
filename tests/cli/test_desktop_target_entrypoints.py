"""The picker covers retained launchers without intercepting explicit commands."""

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from typer.testing import CliRunner

from mokli.cli import commands, desktop_target, entry


@pytest.mark.parametrize("args", [[], ["mokli"]])
def test_retained_launcher_attaches_without_starting_python(monkeypatch, args):
    seen = []

    def dispatch(raw):
        seen.append(raw)
        return 0

    monkeypatch.setattr(desktop_target, "dispatch_bare_desktop_target", dispatch)
    monkeypatch.setattr(entry, "_run_agent", lambda *_a, **_kw: pytest.fail("agent started"))
    # Callback exits before mokli can inspect/load config or start its runtime.
    monkeypatch.setattr(
        "mokli.cli.mokli._resolve_mokli_config_path",
        lambda *_a, **_kw: pytest.fail("Python Mokli started"),
    )
    result = CliRunner().invoke(commands.app, args)
    assert result.exit_code == 0, result.output
    assert seen == [args]


@pytest.mark.parametrize("args", [[], ["mokli"]])
@pytest.mark.parametrize("launcher", ["modern", "retained"])
def test_launcher_picker_ctrl_c_does_not_start_python(monkeypatch, args, launcher):
    class Target:
        def request(self, operation):
            assert operation == "status", "cancelled picker must not request attachment"
            return desktop_target.DesktopReply("ready", frozenset({"mokli", "tui"}))

    monkeypatch.setattr(desktop_target, "_interactive_shell", lambda: True)
    monkeypatch.setattr(desktop_target, "discover_desktop_target", Target)
    monkeypatch.setattr(entry, "_run_agent", lambda *_a, **_kw: pytest.fail("agent started"))
    monkeypatch.setattr(
        "mokli.cli.mokli._resolve_mokli_config_path",
        lambda *_a, **_kw: pytest.fail("Python Mokli started"),
    )
    monkeypatch.setattr(entry.sys, "argv", ["mokli", *args])
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            pipe_input.send_text("\x03")
            if launcher == "retained":
                result = CliRunner().invoke(commands.app, args)
                assert result.exit_code == 130, result.output
            else:
                with pytest.raises(SystemExit) as exc:
                    entry.main()
                assert exc.value.code == 130


@pytest.mark.parametrize("args", [["agent", "--help"], ["--help"], ["--version"],
                                  ["mokli", "--no-open"], ["mokli", "--port", "8765"]])
def test_retained_launcher_explicit_commands_never_discover(monkeypatch, args):
    monkeypatch.setattr(desktop_target, "_interactive_shell", lambda: True)
    monkeypatch.setattr(
        desktop_target, "discover_desktop_target", lambda: pytest.fail("explicit discovery")
    )
    class PythonMokliReachedError(Exception):
        pass

    def stop_mokli(*_args, **_kwargs):
        raise PythonMokliReachedError

    monkeypatch.setattr("mokli.cli.mokli._resolve_mokli_config_path", stop_mokli)
    result = CliRunner().invoke(commands.app, args)
    if args[0] == "mokli":
        assert isinstance(result.exception, PythonMokliReachedError), result.output
    else:
        assert result.exit_code == 0, result.output


def test_modern_mokli_invocation_prompts_once(monkeypatch):
    calls = []

    def dispatch(args):
        calls.append(args)
        return 0

    monkeypatch.setattr(desktop_target, "dispatch_bare_desktop_target", dispatch)
    monkeypatch.setattr(entry.sys, "argv", ["mokli", "mokli"])
    with pytest.raises(SystemExit) as exc:
        entry.main()
    assert exc.value.code == 0
    assert calls == [["mokli"]]
