query "scans/{id}/upload" verb=POST {
  api_group = "mirror"
  description = "Receive the resized (<=1600px) selfie as a private attachment. Deleted after render unless the client keeps scans for progress tracking."
  auth = "user"
  input {
    text id
    file? image
  }
  stack {
    db.query "scan" {
      where = $db.scan.ref == $input.id
      return = { type: "single" }
    } as $scan

    precondition ($scan != null) {
      error_type = "notfound"
      error = "scan_not_found"
    }

    precondition ($input.image != null) {
      error_type = "inputerror"
      error = "image_required"
    }

    storage.create_attachment {
      value = $input.image
      access = "private"
      filename = $input.image.name
    } as $stored

    db.edit "scan" {
      field_name = "id"
      field_value = $scan.id
      data = { image: $stored }
    } as $updated

    storage.sign_private_url {
      pathname = $stored.path
      ttl = 900
    } as $signed_url
  }
  response = { scan_id: $scan.ref, image_url: $signed_url, expires_in: 900 }
  guid = "zwfgw7hcFoqKNA0dL_Hbkv3CTTA"
}
