function "esign/access_token" {
  description = "Foxit eSign OAuth2 client-credentials exchange. Uses the Xano-only FOXIT_ESIGN_* env vars; the agent process never holds these."
  input {
  }
  stack {
    api.request {
      url = $env.FOXIT_ESIGN_BASE_URL ~ "/api/oauth2/access_token"
      method = "POST"
      params = {
        client_id: $env.FOXIT_ESIGN_CLIENT_ID,
        client_secret: $env.FOXIT_ESIGN_CLIENT_SECRET,
        grant_type: "client_credentials",
        scope: "read-write"
      }
      headers = ["Content-Type: application/x-www-form-urlencoded"]
      timeout = 30
    } as $token_result

    precondition ($token_result.response.status == 200) {
      error_type = "standard"
      error = "esign_token_exchange_failed"
    }
  }
  response = $token_result.response.result.access_token
}
