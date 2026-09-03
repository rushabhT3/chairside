function "esign/regenerate_session" {
  description = "POST /api/embedded/regenerateEmbeddedSigningSession: fresh embedded session URL for a signer whose previous session expired unsigned"
  input {
    text folder_id
    email signer_email filters=trim|lower
  }
  stack {
    function.run "esign/access_token" {
      input = {}
    } as $access_token

    api.request {
      url = $env.FOXIT_ESIGN_BASE_URL ~ "/api/embedded/regenerateEmbeddedSigningSession"
      method = "POST"
      params = {
        folderId: $input.folder_id,
        emailIdOfSigner: $input.signer_email
      }
      headers = [
        "Content-Type: application/json",
        "Authorization: Bearer " ~ $access_token
      ]
      timeout = 30
    } as $session_result

    precondition ($session_result.response.status >= 200 && $session_result.response.status < 300) {
      error_type = "standard"
      error = "esign_regenerate_failed"
    }

    var $body { value = $session_result.response.result }
  }
  response = {
    session_url: $body.embeddedSessionURL,
    embedded_token: $body.embeddedToken
  }
  guid = "_R-VJl-c-rD_4HxtrL_j0RZ6PB4"
}
