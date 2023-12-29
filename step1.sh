```shellscript
#!/bin/bash

# Set the server URI
SERVER_URI="https://nc.domain.tld"

# Set the username for authentication
USERNAME="your_username"

# Set the password for authentication
PASSWORD="your_password"

# Set the local path for the XML file
XML_FILE_PATH="./result.xml"

# Set the API path for accessing the trashbin
API_PATH="remote.php/dav/trashbin/<your_username>/trash"

# Construct the XML request body for the PROPFIND request
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

# Execute the PROPFIND request using curl
# Save the response to the local XML file
curl "$SERVER_URI/$API_PATH/" \
  -H 'Content-Type: application/xml; charset=UTF-8' \
  -H 'Depth: 1' \
  -X PROPFIND \
  --data-binary "$REQUEST_BODY" \
  --user "$USERNAME:$PASSWORD" \
  > "$XML_FILE_PATH"

# Print a message indicating the XML response has been saved
echo "XML response saved to: $XML_FILE_PATH"
```