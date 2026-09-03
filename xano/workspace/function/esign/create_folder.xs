function "esign/create_folder" {
  description = "POST /api/folders/createfolder with a base64 PDF and an embedded signing session for one signer. Returns folder id + short-lived session URL."
  input {
    text folder_name
    text pdf_base64 { sensitive = true }
    text file_name
    text signer_first_name
    text signer_last_name
    email signer_email filters=trim|lower
  }
  stack {
    function.run "esign/access_token" {
      input = {}
    } as $access_token

    api.request {
      url = $env.FOXIT_ESIGN_BASE_URL ~ "/api/folders/createfolder"
      method = "POST"
      params = {
        folderName: $input.folder_name,
        sendNow: false,
        processTextTags: true,
        inputType: "base64",
        base64FileString: [$input.pdf_base64],
        fileNames: [$input.file_name],
        createEmbeddedSigningSession: true,
        embeddedSignersEmailIds: [$input.signer_email],
        parties: [
          {
            firstName: $input.signer_first_name,
            lastName: $input.signer_last_name,
            emailId: $input.signer_email,
            permission: "FILL_FIELDS_AND_SIGN",
            sequence: 1
          }
        ]
      }
      headers = [
        "Content-Type: application/json",
        "Authorization: Bearer " ~ $access_token
      ]
      timeout = 60
    } as $create_result

    precondition ($create_result.response.status >= 200 && $create_result.response.status < 300) {
      error_type = "standard"
      error = "esign_create_folder_failed"
    }

    var $body { value = $create_result.response.result }
    var $session { value = $body.embeddedSigningSessions|first }
  }
  response = {
    folder_id: $body.folder.folderId,
    session_url: $session.embeddedSessionURL,
    embedded_token: $session.embeddedToken,
    signer_email: $session.emailIdOfSigner
  }
}
