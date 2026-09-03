query "scans" verb=POST {
  api_group = "mirror"
  description = "Start a scan for a consultation. Returns the scan id and the upload endpoint the phone posts the resized selfie to (Xano accepts uploads on a file input; there is no pre-signed PUT URL)."
  auth = "user"
  input {
    text consultation_id
  }
  stack {
    db.query "consultation" {
      where = $db.consultation.ref == $input.consultation_id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    db.get "client" {
      field_name = "id"
      field_value = $consultation.client_id
    } as $client

    precondition ($auth.role != "client" || $client.user_id == $auth.id) {
      error_type = "accessdenied"
      error = "not_your_consultation"
    }

    security.create_uuid as $ref

    db.add "scan" {
      data = {
        ref: $ref,
        salon_id: $consultation.salon_id,
        client_id: $consultation.client_id,
        consultation_ref: $consultation.ref,
        retained: $client.retained,
        as_of: now
      }
    } as $scan
  }
  response = {
    scan_id: $scan.ref,
    upload_url: $env.$api_baseurl ~ "/api:chairside-mirror/scans/" ~ $scan.ref ~ "/upload"
  }
  guid = "QfnomWkHdzESTQdEq-vx0CYtVtE"
}
