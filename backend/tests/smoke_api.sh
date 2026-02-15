#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000/api/v1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin123}"
TMP_DIR="${TMP_DIR:-/tmp/opsmanus-smoke}"
mkdir -p "$TMP_DIR"

json_get() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"
}

echo "[1] /auth/status"
curl -sS "$BASE_URL/auth/status"
echo

echo "[2] /auth/login"
LOGIN_BODY=$(curl -sS -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")
echo "$LOGIN_BODY"
ACCESS_TOKEN=$(printf '%s' "$LOGIN_BODY" | json_get 'd.get("data",{}).get("access_token","")')
REFRESH_TOKEN=$(printf '%s' "$LOGIN_BODY" | json_get 'd.get("data",{}).get("refresh_token","")')
if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "ERROR: login failed"
  exit 1
fi
AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

echo "[3] /auth/refresh"
curl -sS -X POST "$BASE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
echo

echo "[4] /sessions (create/get/list/share/public)"
CREATE_BODY=$(curl -sS -X PUT "$BASE_URL/sessions" -H "$AUTH_HEADER")
echo "$CREATE_BODY"
SESSION_ID=$(printf '%s' "$CREATE_BODY" | json_get 'd.get("data",{}).get("session_id","")')
if [[ -z "$SESSION_ID" ]]; then
  echo "ERROR: create session failed"
  exit 1
fi
curl -sS "$BASE_URL/sessions" -H "$AUTH_HEADER"
echo
curl -sS "$BASE_URL/sessions/$SESSION_ID" -H "$AUTH_HEADER"
echo
curl -sS -X POST "$BASE_URL/sessions/$SESSION_ID/share" -H "$AUTH_HEADER"
echo
curl -sS "$BASE_URL/sessions/shared/$SESSION_ID"
echo

echo "[5] /files (upload/info/download/signed-url/delete)"
echo "smoke-file-content" > "$TMP_DIR/test.txt"
UPLOAD_BODY=$(curl -sS -X POST "$BASE_URL/files" \
  -H "$AUTH_HEADER" \
  -F "file=@$TMP_DIR/test.txt;type=text/plain")
echo "$UPLOAD_BODY"
FILE_ID=$(printf '%s' "$UPLOAD_BODY" | json_get 'd.get("data",{}).get("file_id","")')
if [[ -z "$FILE_ID" ]]; then
  echo "ERROR: upload file failed"
  exit 1
fi
curl -sS "$BASE_URL/files/$FILE_ID/info" -H "$AUTH_HEADER"
echo
DL_CODE=$(curl -sS -o "$TMP_DIR/down.txt" -w "%{http_code}" "$BASE_URL/files/$FILE_ID/download" -H "$AUTH_HEADER")
echo "download http=$DL_CODE content=$(cat "$TMP_DIR/down.txt")"

SIGNED_BODY=$(curl -sS -X POST "$BASE_URL/files/$FILE_ID/signed-url" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"expire_minutes":5}')
echo "$SIGNED_BODY"
SIGNED_URL=$(printf '%s' "$SIGNED_BODY" | json_get 'd.get("data",{}).get("signed_url","")')
if [[ -n "$SIGNED_URL" ]]; then
  S_CODE=$(curl -sS -o "$TMP_DIR/down2.txt" -w "%{http_code}" "http://127.0.0.1:8000$SIGNED_URL")
  echo "signed-download http=$S_CODE content=$(cat "$TMP_DIR/down2.txt")"
fi

echo "[6] cleanup"
curl -sS -X DELETE "$BASE_URL/files/$FILE_ID" -H "$AUTH_HEADER"
echo
curl -sS -X DELETE "$BASE_URL/sessions/$SESSION_ID/share" -H "$AUTH_HEADER"
echo
curl -sS -X DELETE "$BASE_URL/sessions/$SESSION_ID" -H "$AUTH_HEADER"
echo

echo "SMOKE TEST PASSED"
