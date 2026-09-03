function "esign/get_folder" {
  description = "GET /api/folders/getfolder for one folder id (free status check)"
  input {
    text folder_id
  }
  stack {
    function.run "esign/access_token" {
      input = {}
    } as $access_token

    api.request {
      url = $env.FOXIT_ESIGN_BASE_URL ~ "/api/folders/getfolder?folderId=" ~ ($input.folder_id|url_encode)
      method = "GET"
      headers = ["Authorization: Bearer " ~ $access_token]
      timeout = 30
    } as $folder_result

    precondition ($folder_result.response.status == 200) {
      error_type = "standard"
      error = "esign_get_folder_failed"
    }
  }
  response = $folder_result.response.result
  guid = "mNLCCLQZMNdhwWNryi_XnmWGg8Y"
}
