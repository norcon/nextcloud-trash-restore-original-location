import subprocess
import os
from concurrent.futures import ThreadPoolExecutor


SERVER_URI="https://nextcloud.domain.tld"
LOCAL_DOWNLOAD_PATH="/Users/path/to/restore/folder"
USERNAME="your_username"
PASSWORD="your_password"

# XML-Datei
xml_file = "result.xml"

# Initialisierung des Arrays
values_array = [None, None, None, None]

# XMLStarlet-Befehl für Dateinamen
command = ["xmlstarlet", "sel", "-t", "-v", "//d:multistatus/d:response/d:propstat/d:prop/nc:trashbin-filename", "-nl", xml_file]

# Ausführung des Befehls
output = subprocess.check_output(command, text=True)

# Aufteilen der Ausgabe in ein Array
values_array[0] = output.splitlines()

# XMLStarlet-Befehl für Pfade
command = ["xmlstarlet", "sel", "-t", "-v", "//d:multistatus/d:response/d:propstat/d:prop/nc:trashbin-original-location", "-nl", xml_file]

# Ausführung des Befehls
output = subprocess.check_output(command, text=True)

# Aufteilen der Ausgabe in ein Array
values_array[1] = output.splitlines()


# XMLStarlet-Befehl für Dateinamen
command = ["xmlstarlet", "sel", "-t", "-v", "d:multistatus/d:response/d:propstat/d:prop/d:getcontenttype", "-nl", xml_file]

# Ausführung des Befehls
output = subprocess.check_output(command, text=True)

# Aufteilen der Ausgabe in ein Array
values_array[2] = output.splitlines()

# XMLStarlet-Befehl für href
command = ["xmlstarlet", "sel", "-t", "-v", "d:multistatus/d:response/d:href", "-nl", xml_file]

# Ausführung des Befehls
output = subprocess.check_output(command, text=True)

# Aufteilen der Ausgabe in ein Array
values_array[3] = output.splitlines()

# Filtern leere Elemente und Entfernen von name aus path
filtered_values_array = list(zip(values_array[0], values_array[1], values_array[2], values_array[3]))


def download_file(info):
    name, path, typ, href = info
    if name and path and typ and href:
        path = path.replace(name, "")
        if not path:
           return
        # Erstellen des Zielverzeichnisses
        download_directory = LOCAL_DOWNLOAD_PATH + "/" + path
        download_directory_and_name = LOCAL_DOWNLOAD_PATH + "/" + path + name

        os.makedirs(download_directory, exist_ok=True)

        # Aufbau des curl-Befehls
        curl_command = [
            "curl",
            "--retry", "999",  # Anzahl der Wiederholungsversuche
            "--retry-delay", "5",  # Verzögerung zwischen den Versuchen in Sekunden
            SERVER_URI + href,
            "--output", download_directory_and_name,
            "--user", f"{USERNAME}:{PASSWORD}",
        ]

        # Ausgabe des curl-Befehls für Debugging-Zwecke
        print("Curl command:", " ".join(curl_command))

        subprocess.run(curl_command, check=True)
        print(f"Downloaded: {name} to {download_directory}")


# Anzahl der parallelen Threads festlegen
max_parallel_threads = 30

# Ausgabe der ersten 10 Ergebnisse parallel herunterladen
with ThreadPoolExecutor(max_workers=max_parallel_threads) as executor:
    executor.map(download_file, filtered_values_array)
