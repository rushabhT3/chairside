query "consultations/{id}" verb=GET {
  api_group = "mirror"
  description = "Client view of one consultation. Staff-only competitor reviews are never included here."
  auth = "user"
  input {
    text id
  }
  stack {
    db.query "consultation" {
      where = $db.consultation.ref == $input.id
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

    function.run "snapshot/consultation" {
      input = { ref: $input.id, include_reviews: false }
    } as $projection
  }
  response = $projection
  guid = "0yCsjGQQJZHIJZHnWmHMqZ--fNM"
}
