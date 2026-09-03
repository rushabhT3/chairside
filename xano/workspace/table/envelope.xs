table "envelope" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    int document_id { table = "document" }
    enum kind { values = ["platform_agreement", "consent"] }
    text signer_name
    email signer_email filters=trim|lower
    enum state?="draft" { values = ["draft", "human_reviewed", "sent", "signed", "expired"] }
    text provider_id?
    text session_url? { sensitive = true }
    timestamp expires_at?
    int reviewed_by_user_id? { table = "user" }
    timestamp reviewed_at?
    timestamp sent_at?
    timestamp signed_at?
    int signed_document_id? { table = "document" }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "state"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
    {type: "btree", field: [{name: "provider_id"}]}
  ]
}
