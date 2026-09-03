query "onboarding/{salon_id}" verb=GET {
  api_group = "floor"
  description = "Act 1 as a live log: the onboarding steps written by the agent"
  auth = "user"
  input {
    int salon_id { table = "salon" }
  }
  stack {
    function.run "rbac/require_staff" {
      input = { role: $auth.extras.role, salon_id: $auth.extras.salon_id, expected_salon_id: $input.salon_id }
    } as $allowed

    db.query "onboarding" {
      where = $db.onboarding.salon_id == $input.salon_id
      return = { type: "single" }
    } as $onboarding

    precondition ($onboarding != null) {
      error_type = "notfound"
      error = "onboarding_not_found"
    }
  }
  response = $onboarding
  guid = "TG-BU4rs80E16CT1AdFYvzvqbRI"
}
