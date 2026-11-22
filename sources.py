"""Pull-based ingesters. Each is sync, idempotent, and skips itself when its env vars are unset."""
import base64
import email
import imaplib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.policy import default as email_policy
from email.utils import parsedate_to_datetime
from pathlib import Path

import db
import company_brain_client

BACKFILL = timedelta(days=int(os.getenv("BACKFILL_DAYS", "14")))
MAX_BODY = 3000  # ponytail: truncate long docs/emails; store diffs instead once Drive edits matter
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _cursor(source):
    return datetime.fromisoformat(db.latest(source) or db.iso(datetime.now(timezone.utc) - BACKFILL))


def _http_json(url, headers, method="GET"):
    req = urllib.request.Request(url, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _drive_credentials():
    """Load user OAuth credentials, falling back to an existing service account."""
    oauth_client = os.getenv("GOOGLE_OAUTH_CLIENT_FILE")
    if oauth_client:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        token_file = Path(os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "drive-token.json"))
        creds = Credentials.from_authorized_user_file(token_file, DRIVE_SCOPES) if token_file.exists() else None
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = InstalledAppFlow.from_client_secrets_file(oauth_client, DRIVE_SCOPES).run_local_server(port=0)
            token_file.write_text(creds.to_json())
        return creds

    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if key_file:
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(key_file, scopes=DRIVE_SCOPES)
    return None


def drive():
    creds = _drive_credentials()
    if not creds:
        return
    from googleapiclient.discovery import build

    svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    after = _cursor("drive").strftime("%Y-%m-%dT%H:%M:%S")  # Drive reads naive RFC 3339 as UTC
    # ponytail: first page only (200 files per 15 min poll); add nextPageToken loop if the drive gets busier
    folder = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    query = f"modifiedTime > '{after}' and trashed = false"
    if folder:
        query += f" and '{folder}' in parents"
    files = svc.files().list(
        q=query,
        corpora="allDrives", includeItemsFromAllDrives=True, supportsAllDrives=True,
        orderBy="modifiedTime", pageSize=200,
        fields="files(id,name,mimeType,modifiedTime,webViewLink,lastModifyingUser/displayName)",
    ).execute().get("files", [])
    for f in files:
        text = f"Edited file: {f['name']}"
        if f["mimeType"] == "application/vnd.google-apps.document":
            body = svc.files().export(fileId=f["id"], mimeType="text/plain").execute().decode("utf-8", "ignore")
            text += "\n" + body[:MAX_BODY]
        db.add("drive", f"{f['id']}@{f['modifiedTime']}", f["modifiedTime"],
               f.get("lastModifyingUser", {}).get("displayName"), f["name"], text, f.get("webViewLink"))
        company_brain_client.ingest(
            "drive", f["id"], f["modifiedTime"],
            f.get("lastModifyingUser", {}).get("displayName"), f["name"], text,
            f.get("webViewLink"), revision=f["modifiedTime"],
        )


def zoom():
    account = os.getenv("ZOOM_ACCOUNT_ID")
    if not account:
        return
    basic = base64.b64encode(f"{os.environ['ZOOM_CLIENT_ID']}:{os.environ['ZOOM_CLIENT_SECRET']}".encode()).decode()
    token = _http_json(f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account}",
                       {"Authorization": f"Basic {basic}"}, method="POST")["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    frm = _cursor("zoom").date().isoformat()
    to = datetime.now(timezone.utc).date().isoformat()
    listing = _http_json(f"https://api.zoom.us/v2/meetings/meeting_summaries?from={frm}&to={to}&page_size=300", auth)
    for s in listing.get("summaries", []):
        uuid = s["meeting_uuid"]
        enc = urllib.parse.quote(uuid, safe="")
        if uuid.startswith("/") or "//" in uuid:  # Zoom requires double-encoding for these
            enc = urllib.parse.quote(enc, safe="")
        d = _http_json(f"https://api.zoom.us/v2/meetings/{enc}/meeting_summary", auth)
        parts = [d.get("summary_overview", "")]
        parts += [f"{x.get('label', '')}: {x.get('summary', '')}" for x in d.get("summary_details", [])]
        if d.get("next_steps"):
            parts.append("Next steps:\n" + "\n".join(f"- {n}" for n in d["next_steps"]))
        db.add("zoom", uuid, d.get("meeting_start_time") or s.get("meeting_start_time"),
               d.get("meeting_host_email"), d.get("meeting_topic") or s.get("meeting_topic"),
               "\n".join(p for p in parts if p), d.get("summary_doc_url"))


def invoices():
    host = os.getenv("EMAIL_HOST")
    if not host:
        return
    query = os.getenv("EMAIL_SEARCH", "OR SUBJECT invoice SUBJECT receipt")
    day = _cursor("email").strftime("%d-%b-%Y")
    with imaplib.IMAP4_SSL(host) as m:
        m.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASSWORD"])
        m.select(os.getenv("EMAIL_FOLDER", "INBOX"), readonly=True)
        _, ids = m.search(None, f"(SINCE {day} {query})")
        for i in ids[0].split():
            _, data = m.fetch(i, "(BODY.PEEK[])")
            msg = email.message_from_bytes(data[0][1], policy=email_policy)
            body = msg.get_body(("plain", "html"))
            text = body.get_content() if body else ""
            if body and body.get_content_type() == "text/html":
                text = re.sub(r"<[^>]+>", " ", text)  # ponytail: crude tag strip, good enough for an LLM
            text = re.sub(r"\s+", " ", text)[:MAX_BODY]
            files = [p.get_filename() for p in msg.iter_attachments() if p.get_filename()]
            if files:
                text += "\nAttachments: " + ", ".join(files)
            mid = msg["Message-ID"] or f"{msg['Date']}|{msg['Subject']}"
            url = ""
            if "gmail" in host:
                url = "https://mail.google.com/mail/u/0/#search/rfc822msgid:" + urllib.parse.quote(mid.strip("<>"))
            sent = parsedate_to_datetime(msg["Date"]) if msg["Date"] else datetime.now(timezone.utc)
            db.add("email", mid, sent, msg["From"], msg["Subject"], text, url)


ALL = (drive, zoom, invoices)
