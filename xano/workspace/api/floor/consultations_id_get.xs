query "consultations/{id}" verb=GET {
  api_group = "floor"
  description = "Consultation detail for Floor, including the consultation_event stream and staff-only competitor review notes"
  auth = "user"
  input {
    text id
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.role, salon_id: $auth.salon_id, expected_salon_id: null }
    } as $allowed

    db.query "consultation" {
      where = $db.consultation.ref == $input.id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    precondition ($consultation.salon_id == $auth.salon_id) {
      error_type = "accessdenied"
      error = "salon_mismatch"
    }

    function.run "snapshot/consultation" {
      input = { ref: $input.id, include_reviews: true }
    } as $projection
  }
  response = $projection
}
