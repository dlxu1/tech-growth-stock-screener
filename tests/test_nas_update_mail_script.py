import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nas_update_and_mail.sh"


class NasUpdateMailScriptTest(unittest.TestCase):
    def test_script_sends_success_and_failure_mail_from_nas_host(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('"$DOCKER_BIN" compose run --rm update-report', text)
        self.assertIn("daily_email_latest.txt", text)
        self.assertIn("daily_email_subject.txt", text)
        self.assertIn("tail -200", text)
        self.assertIn('MAIL_BIN="${MAIL_BIN:-mail}"', text)
        self.assertIn('DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"', text)
        self.assertIn('-s "$subject"', text)
        self.assertIn('-s "股票数据更新失败', text)
        self.assertIn("MAIL_TO", text)
        self.assertNotIn("smtplib", text)


if __name__ == "__main__":
    unittest.main()
