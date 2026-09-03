query "onboarding" verb=PATCH {
  api_group = "agent"
  description = "The Onboarding Agent writes its live log here: the ordered steps with status and detail, plus the overall state"
  auth = "user"
  input {
    json steps
    enum state?="running" { values = ["running", "done", "needs_attention"] }
    text failing_step?
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.extras.role }
    } as $allowed

    db.query "onboarding" {
      where = $db.onboarding.salon_id == $auth.extras.salon_id
      return = { type: "single" }
    } as $existing

    conditional {
      if ($existing == null) {
        db.add "onboarding" {
          data = { salon_id: $auth.extras.salon_id, steps: $input.steps, state: $input.state, failing_step: $input.failing_step, updated_at: now }
        } as $onboarding
      }
      else {
        db.edit "onboarding" {
          field_name = "id"
          field_value = $existing.id
          data = { steps: $input.steps, state: $input.state, failing_step: $input.failing_step, updated_at: now }
        } as $onboarding
      }
    }
  }
  response = $onboarding
  guid = "EUypeiZDJt9qtq0x7rB3ad6URJU"
}
