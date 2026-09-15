import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "patcher" / "dd_beekeeper_vita_patcher.py"
spec = importlib.util.spec_from_file_location("dd_beekeeper_vita_patcher", MODULE)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


class PatcherSafetyTests(unittest.TestCase):
    def test_overlay_mod_does_not_copy_pc_audio_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stage = root / "stage"
            mod = root / "mod"
            stage.mkdir()
            (mod / "heroes" / "beekeeper").mkdir(parents=True)
            (mod / "heroes" / "beekeeper" / "marker.txt").write_text("hero", encoding="utf-8")
            (mod / "audio" / "secondary_banks").mkdir(parents=True)
            (mod / "audio" / "secondary_banks" / "hero_beekeeper.bank").write_bytes(b"PC_FMOD_BANK")
            (mod / "audio" / "beekeeper.campaign.guid_overrides.json").write_text("{}", encoding="utf-8")
            (mod / "audio" / "beekeeper.campaign.load_order.json").write_text("{}", encoding="utf-8")
            (mod / "preview_icon.png").write_bytes(b"PREVIEW")
            (mod / "preview_icon.txt").write_text("generated sidecar", encoding="utf-8")

            patcher.overlay_mod(stage, mod)

            self.assertTrue((stage / "heroes" / "beekeeper" / "marker.txt").exists())
            self.assertFalse((stage / "preview_icon.png").exists())
            self.assertFalse((stage / "preview_icon.txt").exists())
            self.assertFalse((stage / "audio" / "secondary_banks" / "hero_beekeeper.bank").exists())
            self.assertFalse((stage / "audio" / "beekeeper.campaign.guid_overrides.json").exists())
            self.assertFalse((stage / "audio" / "beekeeper.campaign.load_order.json").exists())

    def test_update_manifest_removes_extraction_helper_instead_of_packing_it(self):
        with tempfile.TemporaryDirectory() as td:
            stage = Path(td)
            (stage / "PSArcManifest.bin").write_text("helper", encoding="utf-8")
            (stage / "real_file.txt").write_text("game data", encoding="utf-8")

            patcher.update_manifest(stage)

            self.assertFalse((stage / "PSArcManifest.bin").exists())
            self.assertTrue((stage / "real_file.txt").exists())

    def test_prepare_audio_output_never_exports_incompatible_pc_bank(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mod = root / "mod"
            out = root / "out"
            bank = mod / "audio" / "secondary_banks" / "hero_beekeeper.bank"
            bank.parent.mkdir(parents=True)
            bank.write_bytes(b"PC_FMOD_BANK")

            patcher.prepare_audio_output(mod, out)

            self.assertFalse((out / patcher.TITLE_ID / "audio" / "secondary_banks" / "hero_beekeeper.bank").exists())
            self.assertFalse((out / patcher.TITLE_ID / "audio" / "load_order.json").exists())

    def test_release_version_is_1_0_0(self):
        self.assertEqual(patcher.VERSION, "1.0.0")

    def test_cli_no_longer_accepts_audio_load_order(self):
        parser = patcher.build_arg_parser()
        option_strings = {opt for action in parser._actions for opt in action.option_strings}
        self.assertNotIn("--audio-load-order", option_strings)


    def test_psarc_extract_command_uses_supported_argument_form(self):
        cmd = patcher.build_extract_command(Path("tool.exe"), Path("base.psarc"), Path("stage"))
        self.assertEqual(cmd, [
            Path("tool.exe"), "extract", "-y", Path("base.psarc"), "--to=stage"
        ])

    def test_psarc_create_command_uses_attached_short_options(self):
        cmd = patcher.build_create_command(Path("tool.exe"), Path("out.psarc"), Path("files.txt"))
        self.assertEqual(cmd, [
            Path("tool.exe"), "create", "-y", "-C", "-R", "--level=9",
            "-Ifiles.txt", "-oout.psarc"
        ])



if __name__ == "__main__":
    unittest.main()
