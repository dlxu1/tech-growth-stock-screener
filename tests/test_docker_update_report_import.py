import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


class DockerUpdateReportImportTest(unittest.TestCase):
    def test_importable_as_package_module_without_scripts_path_preloaded(self) -> None:
        scripts_path = str(SCRIPTS_DIR)
        original_path = list(sys.path)
        for name in ["scripts.docker_update_report", "docker_update_report"]:
            sys.modules.pop(name, None)
        try:
            sys.path = [item for item in sys.path if item != scripts_path]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            module = importlib.import_module("scripts.docker_update_report")

            self.assertTrue(hasattr(module, "_dashboard_args"))
            self.assertIn(scripts_path, sys.path)
        finally:
            sys.path = original_path


if __name__ == "__main__":
    unittest.main()
