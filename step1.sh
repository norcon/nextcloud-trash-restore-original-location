#!/bin/bash

SERVER_URI="https://nc.domain.tld"
USERNAME="your_username"
PASSWORD="your_password"
XML_FILE_PATH="./result.xml"
API_PATH="remote.php/dav/trashbin/<your_username>/trash"


# PROPFIND request to get information about deleted files
REQUEST_BODY=$(cat <<EOF
<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://nextcloud.org/ns">
    <d:prop>
        <oc:trashbin-original-filename />
        <oc:trashbin-original-location />
        <oc:trashbin-delete-datetime />
        <d:getcontentlength />
        <d:resourcetype />
    </d:prop>
</d:propfind>
EOF
)

# Execute PROPFIND request and save the response to a local XML file
curl "$SERVER_URI/$API_PATH/" \
  -H 'Content-Type: application/xml; charset=UTF-8' \
  -H 'Depth: 1' \
  -X PROPFIND \
  --data-binary "$REQUEST_BODY" \
  --user "$USERNAME:$PASSWORD" \
  > "$XML_FILE_PATH"

echo "XML response saved to: $XML_FILE_PATH"
