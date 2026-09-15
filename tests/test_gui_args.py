import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "gui" / "dd_beekeeper_vita_gui.py"
spec = importlib.util.spec_from_file_location("dd_beekeeper_vita_gui", MODULE)
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


class GuiArgumentTests(unittest.TestCase):
    def test_build_patcher_args_has_no_audio_load_order_option(self):
        args = gui.build_patcher_args("base.psarc", "beekeeper.zip", "tools", "output", False)
        self.assertNotIn("--audio-load-order", args)
        self.assertEqual(args[:8], [
            "--psarc", "base.psarc",
            "--mod", "beekeeper.zip",
            "--tools", "tools",
            "--output", "output",
        ])

    def test_build_patcher_args_adds_force_stagecoach_only_when_requested(self):
        normal = gui.build_patcher_args("base.psarc", "beekeeper.zip", "tools", "output", False)
        forced = gui.build_patcher_args("base.psarc", "beekeeper.zip", "tools", "output", True)
        self.assertNotIn("--force-stagecoach", normal)
        self.assertIn("--force-stagecoach", forced)


if __name__ == "__main__":
    unittest.main()
