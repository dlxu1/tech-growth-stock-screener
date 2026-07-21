import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nas_update_and_mail.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    path.chmod(0o755)


class NasUpdateMailScriptTest(unittest.TestCase):
    def _run_script(self, mail_to: str, fail_recipient: str = "", fail_docker: bool = False) -> tuple[subprocess.CompletedProcess, Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root_dir = Path(temp.name)
        fake_docker = root_dir / "fake_docker.sh"
        fake_mail = root_dir / "fake_mail.sh"
        _write_executable(
            fake_docker,
            """
            #!/usr/bin/env bash
            echo "$*" >> "$ROOT_DIR/docker_calls.log"
            if [ "${FAIL_DOCKER:-0}" = "1" ]; then
              echo "fake docker failure"
              exit 7
            fi
            mkdir -p "$ROOT_DIR/nas-cache/reports"
            printf '测试日报正文\\n' > "$ROOT_DIR/nas-cache/reports/daily_email_latest.txt"
            printf '测试日报主题\\n' > "$ROOT_DIR/nas-cache/reports/daily_email_subject.txt"
            exit 0
            """,
        )
        _write_executable(
            fake_mail,
            """
            #!/usr/bin/env bash
            recipient="${@: -1}"
            subject=""
            while [ "$#" -gt 0 ]; do
              case "$1" in
                -s)
                  shift
                  subject="${1:-}"
                  ;;
              esac
              shift || true
            done
            body="$(cat)"
            printf '%s|%s|%s\\n' "$subject" "$recipient" "$body" >> "$ROOT_DIR/mail_calls.log"
            if [ -n "${FAIL_RECIPIENT:-}" ] && [ "$recipient" = "$FAIL_RECIPIENT" ]; then
              exit 9
            fi
            exit 0
            """,
        )
        env = os.environ.copy()
        env.update(
            {
                "ROOT_DIR": str(root_dir),
                "LOG_FILE": str(root_dir / "nas-cache" / "update.log"),
                "DOCKER_BIN": str(fake_docker),
                "MAIL_BIN": str(fake_mail),
                "MAIL_TO": mail_to,
                "FAIL_RECIPIENT": fail_recipient,
                "FAIL_DOCKER": "1" if fail_docker else "0",
            }
        )
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
        return result, root_dir

    def _recipients_from_log(self, root_dir: Path) -> list[str]:
        log = root_dir / "mail_calls.log"
        if not log.exists():
            return []
        return [
            line.split("|", 2)[1]
            for line in log.read_text(encoding="utf-8").splitlines()
            if "|" in line
        ]

    def test_script_still_sends_to_single_recipient(self) -> None:
        result, root_dir = self._run_script("a@example.com")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._recipients_from_log(root_dir), ["a@example.com"])

    def test_script_splits_comma_space_and_semicolon_recipients(self) -> None:
        cases = [
            "a@example.com,b@example.com",
            "a@example.com b@example.com",
            "a@example.com;b@example.com",
        ]
        for mail_to in cases:
            with self.subTest(mail_to=mail_to):
                result, root_dir = self._run_script(mail_to)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self._recipients_from_log(root_dir), ["a@example.com", "b@example.com"])

    def test_script_rejects_empty_recipient_list_after_splitting(self) -> None:
        result, root_dir = self._run_script(" , ; ")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._recipients_from_log(root_dir), [])

    def test_script_continues_after_one_recipient_fails(self) -> None:
        result, root_dir = self._run_script(
            "a@example.com,fail@example.com,b@example.com",
            fail_recipient="fail@example.com",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            self._recipients_from_log(root_dir),
            ["a@example.com", "fail@example.com", "b@example.com"],
        )

    def test_script_sends_update_failure_mail_to_each_recipient(self) -> None:
        result, root_dir = self._run_script("a@example.com,b@example.com", fail_docker=True)

        self.assertEqual(result.returncode, 7)
        self.assertEqual(self._recipients_from_log(root_dir), ["a@example.com", "b@example.com"])

    def test_script_keeps_nas_host_mail_and_docker_tools(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('"$DOCKER_BIN" compose run --rm update-report', text)
        self.assertIn('MAIL_BIN="${MAIL_BIN:-mail}"', text)
        self.assertIn('DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"', text)
        self.assertNotIn("smtplib", text)


if __name__ == "__main__":
    unittest.main()
