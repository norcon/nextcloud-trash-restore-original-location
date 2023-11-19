# nextcloud-trash-restore-original-location
Bash and Python Script to download all files out of Nextcloud Trash bin and store it in original folder structure, because of Nextcloud Trashbin Restore Bug: https://github.com/nextcloud/server/issues/31200

# How to use (Tested with MacOS 14 Sonoma)
Get the XML response from nextcloud Trash Bin via Webdav
1. Put in your Credentials and URL oft the nextcloud instance in file step1.sh
2. run "bash step1.sh" in your Terminal
3. File will be created in your current directoy.

Download each file of your trash bin an create the original folder structure. The nextcloud bug will always restore each file in the root folder. Thants not good :-) 
1. Put in your Credentials, URL and target path on your computer in file step2.py
2. run the script in your terminal: python or pyhton3 step2.py
3. In parallel, all your files will be downloaded. If your server will be busy, decrease the max_parallel_threads in step2.py


