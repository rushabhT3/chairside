query "scans/{id}/complete" verb=POST {
  api_group = "mirror"
  description = "Mark the upload complete with the on-device sha256; the agent uses the hash as the render cache key"
  auth = "user"
  input {
    text id
    text image_sha256 filters=trim|lower|min:64|max:64
    bool retained?=false
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

    db.edit "scan" {
      field_name = "id"
      field_value = $scan.id
      data = { image_sha256: $input.image_sha256, retained: $input.retained }
    } as $updated

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $scan.salon_id,
        consultation_ref: $scan.consultation_ref,
        type: "capture.uploaded",
        payload: { image_sha256: $input.image_sha256, retained: $input.retained, scan_id: $scan.ref },
        ts: $ts,
        actor: "client"
      }
    } as $appended
  }
  response = { scan_id: $scan.ref, image_sha256: $input.image_sha256, retained: $input.retained }
}
