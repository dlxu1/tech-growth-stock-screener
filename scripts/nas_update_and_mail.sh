#!/usr/bin/env bash
set -u

ROOT_DIR="${ROOT_DIR:-/vol1/docker/tech-growth-stock-screener}"
LOG_FILE="${LOG_FILE:-$ROOT_DIR/nas-cache/update.log}"
REPORT_DIR="$ROOT_DIR/nas-cache/reports"
BODY_FILE="$REPORT_DIR/daily_email_latest.txt"
SUBJECT_FILE="$REPORT_DIR/daily_email_subject.txt"
ERROR_BODY_FILE="$REPORT_DIR/daily_email_error_latest.txt"
MAIL_BIN="${MAIL_BIN:-mail}"
DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"
MAIL_RECIPIENTS=()

parse_mail_recipients() {
  MAIL_RECIPIENTS=()
  local raw="${MAIL_TO:-}"
  raw="${raw//,/ }"
  raw="${raw//;/ }"
  local recipient
  for recipient in $raw; do
    if [ -n "$recipient" ]; then
      MAIL_RECIPIENTS+=("$recipient")
    fi
  done
}

send_mail_to_recipients() {
  local subject="$1"
  local body_file="$2"
  local failed=0
  local recipient
  for recipient in "${MAIL_RECIPIENTS[@]}"; do
    if "$MAIL_BIN" -s "$subject" "$recipient" < "$body_file"; then
      echo "[$(date '+%F %T')] email sent to $recipient"
    else
      echo "[$(date '+%F %T')] failed to send email to $recipient"
      failed=1
    fi
  done
  return "$failed"
}

mkdir -p "$(dirname "$LOG_FILE")" "$REPORT_DIR"
exec >> "$LOG_FILE" 2>&1

echo "[$(date '+%F %T')] starting update-report"

parse_mail_recipients
if [ "${#MAIL_RECIPIENTS[@]}" -eq 0 ]; then
  echo "MAIL_TO is required, e.g. MAIL_TO=you@example.com or MAIL_TO=you@example.com,team@example.com $0"
  exit 2
fi

cd "$ROOT_DIR" || exit 2

if "$DOCKER_BIN" compose run --rm update-report; then
  subject="$(cat "$SUBJECT_FILE" 2>/dev/null || echo "股票数据更新日报")"
  if [ -s "$BODY_FILE" ]; then
    if ! send_mail_to_recipients "$subject" "$BODY_FILE"; then
      exit 1
    fi
  else
    echo "daily email body not found: $BODY_FILE"
    tail -200 "$LOG_FILE" > "$ERROR_BODY_FILE"
    send_mail_to_recipients "股票数据更新失败 - 报告文件缺失" "$ERROR_BODY_FILE"
    exit 1
  fi
else
  status=$?
  echo "[$(date '+%F %T')] update-report failed with status $status"
  tail -200 "$LOG_FILE" > "$ERROR_BODY_FILE"
  if ! send_mail_to_recipients "股票数据更新失败 - $(date '+%F')" "$ERROR_BODY_FILE"; then
    exit 1
  fi
  exit "$status"
fi
