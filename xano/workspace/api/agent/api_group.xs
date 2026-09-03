api_group "agent" {
  canonical = "chairside-agent"
  description = "Writes from the agent runtime (service token with role=agent): events, consultation state, catalog, documents, envelopes, orders, bookings, onboarding log. No eSign credential lives on this side."
  tags = ["agent"]
}
