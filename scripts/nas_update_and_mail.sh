#!/usr/bin/env bash
set -u

ROOT_DIR="${ROOT_DIR:-/vol1/docker/tech-growth-stock-screener}"
LOG_FILE="${LOG_FILE:-$ROOT_DIR/nas-cache/update.log}"
REPORT_DIR="$ROOT_DIR/nas-cache/reports"
BODY_FILE="$REPORT_DIR/daily_email_latest.txt"
SUBJECT_FILE="$REPORT_DIR/daily_email_subject.txt"
MAIL_BIN="${MAIL_BIN:-mail}"
DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"

mkdir -p "$(dirname "$LOG_FILE")" "$REPORT_DIR"
exec >> "$LOG_FILE" 2>&1

echo "[$(date '+%F %T')] starting update-report"

if [ -z "${MAIL_TO:-}" ]; then
  echo "MAIL_TO is required, e.g. MAIL_TO=you@example.com $0"
  exit 2
fi

cd "$ROOT_DIR" || exit 2

if "$DOCKER_BIN" compose run --rm update-report; then
  subject="$(cat "$SUBJECT_FILE" 2>/dev/null || echo "股票数据更新日报")"
  if [ -s "$BODY_FILE" ]; then
    if "$MAIL_BIN" -s "$subject" "$MAIL_TO" < "$BODY_FILE"; then
      echo "[$(date '+%F %T')] success email sent to $MAIL_TO"
    else
      echo "[$(date '+%F %T')] failed to send success email to $MAIL_TO"
      exit 1
    fi
  else
    echo "daily email body not found: $BODY_FILE"
    tail -200 "$LOG_FILE" | "$MAIL_BIN" -s "股票数据更新失败 - 报告文件缺失" "$MAIL_TO"
    exit 1
  fi
else
  status=$?
  echo "[$(date '+%F %T')] update-report failed with status $status"
  tail -200 "$LOG_FILE" | "$MAIL_BIN" -s "股票数据更新失败 - $(date '+%F')" "$MAIL_TO"
  exit "$status"
fi
