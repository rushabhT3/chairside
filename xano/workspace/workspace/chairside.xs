workspace "chairside" {
  description = "Chairside: system of record, auth and RBAC, the eSign signing gate, background tasks, static hosting, and the chairside-mcp server"
  env = {
    FOXIT_ESIGN_CLIENT_ID: "",
    FOXIT_ESIGN_CLIENT_SECRET: "",
    FOXIT_ESIGN_BASE_URL: "https://na1.foxitesign.foxit.com",
    SERPAPI_API_KEY: "",
    AUDIT_HMAC_KEY: ""
  }
  acceptance = {
    ai_terms: true
  }
  preferences = {
    track_performance: true
  }
}
