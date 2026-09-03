function "rbac/require_staff" {
  description = "Gate for Floor and Commit endpoints: the JWT role must be owner or stylist; the agent service token and client tokens are rejected with the contract reasons"
  input {
    text role?
    int salon_id?
    int expected_salon_id?
  }
  stack {
    precondition ($input.role != "agent") {
      error_type = "accessdenied"
      error = "agent_token_rejected"
    }
    precondition ($input.role == "owner" || $input.role == "stylist") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }
    conditional {
      if ($input.expected_salon_id != null) {
        precondition ($input.salon_id == $input.expected_salon_id) {
          error_type = "accessdenied"
          error = "salon_mismatch"
        }
      }
    }
  }
  response = true
}
