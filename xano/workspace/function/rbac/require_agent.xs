function "rbac/require_agent" {
  description = "Agent API group: only the agent service token may write events, SKUs, documents and envelopes"
  input {
    text role?
  }
  stack {
    precondition ($input.role == "agent") {
      error_type = "accessdenied"
      error = "agent_token_required"
    }
  }
  response = true
}
