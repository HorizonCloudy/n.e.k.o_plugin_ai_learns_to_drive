"""巡航闸门回归：被拦下不推进 mtime，重试三次后放弃；游戏退出后正常应用。"""
import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    sdk = types.ModuleType("plugin.sdk.plugin")

    class SdkError(Exception):
        pass

    class NekoPluginBase:
        def __init__(self, ctx):
            self.ctx = ctx
            self.config = ctx.config
            self.data_path = ctx.data_path

    def neko_plugin(cls):
        return cls

    def deco(**_kw):
        return lambda fn: fn

    class Ok:
        def __init__(self, value=None):
            self.value = value

    for name, obj in {
        "SdkError": SdkError,
        "NekoPluginBase": NekoPluginBase,
        "neko_plugin": neko_plugin,
        "plugin_entry": deco,
        "llm_tool": deco,
        "lifecycle": deco,
        "Ok": Ok,
        "Err": Ok,
    }.items():
        setattr(sdk, name, obj)
    sys.modules.setdefault("plugin", types.ModuleType("plugin"))
    sys.modules.setdefault("plugin.sdk", types.ModuleType("plugin.sdk"))
    sys.modules["plugin.sdk.plugin"] = sdk

    pkg = types.ModuleType("aldpkg")
    pkg.__path__ = [str(ROOT)]
    sys.modules["aldpkg"] = pkg

    def load(mod_name, file_name):
        spec = importlib.util.spec_from_file_location(mod_name, str(ROOT / file_name))
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        return module

    ald = load("aldpkg.ald", "ald.py")
    load("aldpkg.install", "install.py")
    plugin_mod = load("aldpkg.__init__", "__init__.py")
    return ald, plugin_mod


def _run_case(tmp_path: Path) -> None:
    ald, plugin_mod = _load()
    user = tmp_path / "user"
    (user / "settings").mkdir(parents=True)
    ald.write_json(ald.settings_path(user), {"Evolution": {"MutationRate": 0.2}})
    genome = user / "Beginner-E.evolution"
    ald.write_json(genome, {"Stats": {"Generations": []}})

    ald.newest_genome = lambda _u: genome
    ald.recommend = lambda _g, _s: {"reason": "test", "changes": {"MutationRate": 0.3}}
    ald.is_game_running = lambda _exe=None: True

    cfg = {"user_dir": str(user), "allow_write": True, "auto_apply_after_exit": True, "verify_game": "off"}

    class Dump:
        async def dump(self):
            return {"ald": cfg}

    class Ctx:
        config = Dump()

        def data_path(self, name):
            return tmp_path / name

    plugin = plugin_mod.AiLearnsToDrivePlugin(Ctx())
    plugin._last_genome_mtime = 0.0
    mtime = genome.stat().st_mtime

    for expected_count in (1, 2, 3):
        decision = asyncio.run(plugin._after_game_exit(cfg))
        assert "游戏又打开了" in decision.get("skipped", ""), decision
        assert plugin._last_genome_mtime < mtime, "被拦下后 mtime 不该推进"
        assert plugin._retry_count == expected_count

    decision = asyncio.run(plugin._after_game_exit(cfg))
    assert "三次" in decision.get("skipped", ""), decision
    assert plugin._last_genome_mtime == mtime, "放弃后应推进 mtime"

    plugin._last_genome_mtime = 0.0
    plugin._retry_genome_mtime = 0.0
    plugin._retry_count = 0
    ald.is_game_running = lambda _exe=None: False
    decision = asyncio.run(plugin._after_game_exit(cfg))
    assert decision.get("applied") is True, decision
    assert ald.load_settings(user)["Evolution"]["MutationRate"] == 0.3


def test_cruise_gate_retries_then_applies(tmp_path) -> None:
    _run_case(Path(str(tmp_path)))


if __name__ == "__main__":
    import tempfile

    _run_case(Path(tempfile.mkdtemp()))
    print("cruise gate test ok")
