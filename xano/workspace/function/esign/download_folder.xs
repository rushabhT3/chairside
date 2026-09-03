function "esign/download_folder" {
  description = "GET /api/folders/downloadfolder for a completed folder; returns the raw body so the caller can store it as the signed document"
  input {
    text folder_id
  }
  stack {
    function.run "esign/access_token" {
      input = {}
    } as $access_token

    api.request {
      url = $env.FOXIT_ESIGN_BASE_URL ~ "/api/folders/downloadfolder?folderId=" ~ ($input.folder_id|url_encode)
      method = "GET"
      headers = ["Authorization: Bearer " ~ $access_token]
      timeout = 60
    } as $download_result

    precondition ($download_result.response.status == 200) {
      error_type = "standard"
      error = "esign_download_failed"
    }
  }
  response = $download_result.response.result
  guid = "Je2NpBde-AN1ijbBny2wNucRfco"
}
