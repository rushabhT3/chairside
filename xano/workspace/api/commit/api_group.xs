api_group "commit" {
  canonical = "chairside-commit"
  description = "The signing gate. The only code path in the whole system that can reach Foxit eSign. Requires a human JWT (owner or stylist), a human-reviewed envelope, and consent_ready / docs_reviewed."
  tags = ["commit", "esign", "gate"]
}
