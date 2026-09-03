query "clients/{id}/retention" verb=POST {
  api_group = "mirror"
  description = "Toggle 'Keep my scans for progress tracking' (default off). Applies to future scans and to existing undeleted scans."
  auth = "user"
  input {
    text id
    bool retained
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

    db.edit "client" {
      field_name = "id"
      field_value = $client.id
      data = { retained: $input.retained }
    } as $updated

    db.query "scan" {
      where = $db.scan.client_id == $client.id && $db.scan.deleted == false
      return = { type: "list" }
    } as $scans

    foreach ($scans) {
      each as $scan {
        db.edit "scan" {
          field_name = "id"
          field_value = $scan.id
          data = { retained: $input.retained }
        }
      }
    }
  }
  response = { client_id: $client.ref, retained: $input.retained }
}
