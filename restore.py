#!/usr/bin/env python3
"""Download the Nextcloud trash bin into its original folder structure.

Workaround for https://github.com/nextcloud/server/issues/31200, where
restoring from the trash bin puts every file into the root folder.

Only the Python standard library is used. Files on the server are not
modified or removed; they are only downloaded.
"""

import argparse
import base64
import getpass
import os
import posixpath
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

DAV = "{DAV:}"
NC = "{http://nextcloud.org/ns}"

PROPFIND_BODY = b"""<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns">
  <d:prop>
    <nc:trashbin-filename />
    <nc:trashbin-original-location />
    <nc:trashbin-deletion-time />
    <d:getcontentlength />
    <d:resourcetype />
  </d:prop>
</d:propfind>
"""

RETRIES = 3
CHUNK_SIZE = 1024 * 1024


class Client:
    def __init__(self, base_url, username, password, timeout):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.auth_header = f"Basic {token}"

    def url(self, href):
        # hrefs returned by the server are absolute paths, already URL-encoded
        return urllib.parse.urljoin(self.base_url, href)

    def open(self, href, method="GET", data=None, headers=None):
        req = urllib.request.Request(self.url(href), data=data, method=method)
        req.add_header("Authorization", self.auth_header)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        return urllib.request.urlopen(req, timeout=self.timeout)

    def propfind(self, href):
        headers = {"Depth": "1", "Content-Type": "application/xml; charset=utf-8"}
        with self.open(href, "PROPFIND", PROPFIND_BODY, headers) as resp:
            return ET.fromstring(resp.read())


def parse_entries(tree, request_url):
    """Return one dict per <d:response>, skipping the requested folder itself."""
    own_path = urllib.parse.unquote(urllib.parse.urlparse(request_url).path).rstrip("/")
    entries = []
    for response in tree.findall(f"{DAV}response"):
        href = response.findtext(f"{DAV}href", "")
        if urllib.parse.unquote(urllib.parse.urlparse(href).path).rstrip("/") == own_path:
            continue
        props = {}
        is_collection = False
        for propstat in response.findall(f"{DAV}propstat"):
            # properties the server does not know come back with 404
            if " 200 " not in (propstat.findtext(f"{DAV}status") or "") + " ":
                continue
            prop = propstat.find(f"{DAV}prop")
            if prop is None:
                continue
            for child in prop:
                props[child.tag] = (child.text or "").strip()
            if prop.find(f"{DAV}resourcetype/{DAV}collection") is not None:
                is_collection = True
        entries.append({
            "href": href,
            "name": urllib.parse.unquote(posixpath.basename(href.rstrip("/"))),
            "filename": props.get(f"{NC}trashbin-filename", ""),
            "location": props.get(f"{NC}trashbin-original-location", ""),
            "deleted": int(props.get(f"{NC}trashbin-deletion-time") or 0),
            "size": int(props.get(f"{DAV}getcontentlength") or 0),
            "is_collection": is_collection,
        })
    return entries


def safe_relpath(path):
    """Normalise a server-provided path; reject anything escaping the target."""
    norm = posixpath.normpath("/" + path.replace("\\", "/")).lstrip("/")
    if not norm or norm == "." or any(part == ".." for part in norm.split("/")):
        raise ValueError(f"unsafe path from server: {path!r}")
    return norm


def collect_files(client, trash_href):
    """Walk the trash bin and return (relpath, href, size, deleted) for every file."""
    files = []
    skipped = []

    def walk(href, relpath, deleted):
        for entry in parse_entries(client.propfind(href), client.url(href)):
            child = posixpath.join(relpath, entry["name"])
            if entry["is_collection"]:
                walk(entry["href"], child, deleted)
            else:
                files.append((child, entry["href"], entry["size"], deleted))

    for entry in parse_entries(client.propfind(trash_href), client.url(trash_href)):
        try:
            relpath = safe_relpath(entry["location"] or entry["filename"])
        except ValueError as exc:
            skipped.append(f"{entry['href']}: {exc}")
            continue
        if entry["is_collection"]:
            walk(entry["href"], relpath, entry["deleted"])
        else:
            files.append((relpath, entry["href"], entry["size"], entry["deleted"]))
    return files, skipped


def assign_targets(files):
    """Give every file a unique local path.

    If the same path was deleted several times, the most recently deleted
    version keeps the original name, older ones get the deletion time appended.
    """
    taken = set()
    plan = []
    for relpath, href, size, deleted in sorted(files, key=lambda f: -f[3]):
        target = relpath
        if target in taken:
            stem, ext = posixpath.splitext(relpath)
            stamp = datetime.fromtimestamp(deleted).strftime("%Y-%m-%d %H-%M-%S")
            target = f"{stem} (deleted {stamp}){ext}"
            n = 2
            while target in taken:
                target = f"{stem} (deleted {stamp} {n}){ext}"
                n += 1
        taken.add(target)
        plan.append((target, href, size))
    return sorted(plan)


def download(client, href, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    for attempt in range(1, RETRIES + 1):
        try:
            with client.open(href) as resp, open(part, "wb") as fh:
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
            os.replace(part, dest)
            return
        except (urllib.error.URLError, OSError) as exc:
            if os.path.exists(part):
                os.remove(part)
            # client errors (404, 403, ...) will not go away by retrying
            permanent = isinstance(exc, urllib.error.HTTPError) and exc.code < 500
            if permanent or attempt == RETRIES:
                raise
            time.sleep(2 ** attempt)


def parse_args():
    p = argparse.ArgumentParser(
        description="Download the Nextcloud trash bin into its original folder structure.")
    p.add_argument("--url", default=os.environ.get("NC_URL"),
                   help="Nextcloud base URL, e.g. https://cloud.example.com (env: NC_URL)")
    p.add_argument("--user", default=os.environ.get("NC_USER"),
                   help="Nextcloud username (env: NC_USER)")
    p.add_argument("--target", default=os.environ.get("NC_TARGET"),
                   help="local folder to restore into (env: NC_TARGET)")
    p.add_argument("--workers", type=int, default=4,
                   help="parallel downloads (default: 4)")
    p.add_argument("--timeout", type=float, default=60,
                   help="network timeout in seconds (default: 60)")
    p.add_argument("--overwrite", action="store_true",
                   help="overwrite files that already exist locally")
    p.add_argument("--dry-run", action="store_true",
                   help="only list what would be downloaded")
    args = p.parse_args()
    missing = [name for name in ("url", "user", "target") if not getattr(args, name)]
    if missing:
        p.error("missing " + ", ".join("--" + m for m in missing))
    return args


def main():
    args = parse_args()
    # Never accept the password as an argument: it would be visible in `ps`.
    password = os.environ.get("NC_PASSWORD") or getpass.getpass(
        f"Password (or app password) for {args.user}: ")
    client = Client(args.url, args.user, password, args.timeout)
    trash_href = "remote.php/dav/trashbin/{}/trash/".format(urllib.parse.quote(args.user))
    target_root = os.path.abspath(os.path.expanduser(args.target))

    try:
        files, skipped = collect_files(client, trash_href)
    except urllib.error.HTTPError as exc:
        sys.exit(f"Could not read trash bin: HTTP {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach server: {exc.reason}")

    plan = assign_targets(files)
    todo = []
    existing = 0
    for relpath, href, size in plan:
        dest = os.path.join(target_root, *relpath.split("/"))
        if os.path.exists(dest) and not args.overwrite:
            existing += 1
            continue
        todo.append((relpath, href, size, dest))

    total = sum(t[2] for t in todo)
    print(f"{len(plan)} files in trash, {existing} already present, "
          f"{len(todo)} to download ({total / 1024 / 1024:.1f} MiB) into {target_root}")
    for msg in skipped:
        print(f"SKIPPED {msg}", file=sys.stderr)

    if args.dry_run:
        for relpath, _, size, _ in todo:
            print(f"  {relpath} ({size} bytes)")
        return

    failed = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(download, client, href, dest): relpath
                   for relpath, href, _, dest in todo}
        for i, future in enumerate(as_completed(futures), 1):
            relpath = futures[future]
            try:
                future.result()
                print(f"[{i}/{len(todo)}] {relpath}")
            except Exception as exc:
                failed.append(relpath)
                print(f"[{i}/{len(todo)}] FAILED {relpath}: {exc}", file=sys.stderr)

    print(f"Done: {len(todo) - len(failed)} downloaded, {len(failed)} failed, "
          f"{len(skipped)} skipped.")
    if failed or skipped:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
