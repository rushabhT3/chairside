query "onboarding/{salon_id}/review-docs" verb=POST {
  api_group = "floor"
  description = "The owner confirms they have read the Doctavian document family. Sets onboarding.docs_reviewed, which the Commit Service requires before the platform agreement can be sent."
  auth = "user"
  input {
    int salon_id { table = "salon" }
  }
  stack {
    precondition ($auth.role == "owner" && $auth.salon_id == $input.salon_id) {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.query "onboarding" {
      where = $db.onboarding.salon_id == $input.salon_id
      return = { type: "single" }
    } as $onboarding

    precondition ($onboarding != null) {
      error_type = "notfound"
      error = "onboarding_not_found"
    }

    db.edit "onboarding" {
      field_name = "id"
      field_value = $onboarding.id
      data = { docs_reviewed: true, updated_at: now }
    } as $updated
  }
  response = { salon_id: $input.salon_id, docs_reviewed: true }
}
