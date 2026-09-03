query "clients/{id}/data" verb=DELETE {
  api_group = "mirror"
  description = "'Delete everything now': tombstone the client, drop scan images and scores, and append a data.tombstoned event so the ledger records the deletion without the data"
  auth = "user"
  input {
    text id
  }
  stack {
    db.query "client" {
      where = $db.client.ref == $input.id
      return = { type: "single" }
    } as $client

    precondition ($client != null) {
      error_type = "notfound"
      error = "client_not_found"
    }

    precondition ($auth.role != "client" || $client.user_id == $auth.id) {
      error_type = "accessdenied"
      error = "not_your_record"
    }

    db.query "scan" {
      where = $db.scan.client_id == $client.id && $db.scan.deleted == false
      return = { type: "list" }
    } as $scans

    var $deleted_scans { value = 0 }
    foreach ($scans) {
      each as $scan {
        conditional {
          if ($scan.image != null) {
            storage.delete_file { pathname = $scan.image.path }
          }
        }
        db.edit "scan" {
          field_name = "id"
          field_value = $scan.id
          data = { image: null, scores: null, color_tones: null, hair: null, face: null, deleted: true, retained: false }
        }
        math.add $deleted_scans { value = 1 }
      }
    }

    db.edit "client" {
      field_name = "id"
      field_value = $client.id
      data = { tombstoned: true, tombstoned_at: now, retained: false, allergens: null, email: null }
    } as $tombstoned

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $client.salon_id,
        consultation_ref: null,
        type: "data.tombstoned",
        payload: { client_id: $client.ref, scans_deleted: $deleted_scans },
        ts: $ts,
        actor: "client"
      }
    } as $appended
  }
  response = { client_id: $client.ref, tombstoned: true, scans_deleted: $deleted_scans }
}
