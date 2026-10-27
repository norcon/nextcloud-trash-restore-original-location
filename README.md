# nextcloud-trash-restore-original-location

Python script that downloads all files from the Nextcloud trash bin and stores
them in their **original folder structure** — a workaround for the Nextcloud bug
where restoring from the trash bin puts every file into the root folder:
https://github.com/nextcloud/server/issues/31200

The script only reads from the server. Nothing in your Nextcloud is changed or deleted.

## Features

- Single script, Python 3.8+ standard library only (no `curl`, no `xmlstarlet`)
- Restores files from the root folder and from subfolders
- Restores deleted **folders** including all their contents
- Same file deleted several times? The most recently deleted version keeps its
  name, older versions are saved as `name (deleted YYYY-MM-DD HH-MM-SS).ext`
- Password is never stored in a file, shown in the output or passed on the command line
- Already downloaded files are skipped, so you can simply run it again after an interruption
- Failed downloads are retried and listed at the end
- `--dry-run` shows what would be downloaded

## Usage

```bash
python3 restore.py --url https://cloud.example.com --user alice --target ~/Restored
```

You will be asked for your password. Using a Nextcloud
[app password](https://docs.nextcloud.com/server/latest/user_manual/en/session_management.html#managing-devices)
is recommended (required if you use two-factor authentication).

All options can also be set as environment variables (`NC_URL`, `NC_USER`,
`NC_TARGET`, `NC_PASSWORD`):

| Option | Description |
|---|---|
| `--url` | Nextcloud base URL, including a subpath if Nextcloud is not at the root (e.g. `https://example.com/nextcloud`) |
| `--user` | Nextcloud username |
| `--target` | Local folder to restore into |
| `--workers` | Number of parallel downloads (default: 4). Lower it if your server gets busy |
| `--timeout` | Network timeout in seconds (default: 60) |
| `--overwrite` | Overwrite files that already exist in the target folder |
| `--dry-run` | Only list what would be downloaded |

The exit code is `0` if everything was downloaded and `1` if any file failed or was skipped.

After checking the result you can upload the restored folder back to Nextcloud
(e.g. via the desktop client) and empty the trash bin.

## Kurzanleitung (Deutsch)

Das Skript lädt alle Dateien aus dem Nextcloud-Papierkorb herunter und legt sie in der
ursprünglichen Ordnerstruktur ab. Auf dem Server wird nichts verändert.

```bash
python3 restore.py --url https://cloud.example.com --user alice --target ~/Wiederhergestellt
```

Das Passwort (am besten ein App-Passwort) wird beim Start abgefragt. Mit `--dry-run`
siehst du vorab, was heruntergeladen würde. Bei Abbruch einfach erneut starten –
bereits vorhandene Dateien werden übersprungen.
