table "document" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    enum kind { values = ["platform_agreement", "consent", "intake", "aftercare", "price_list", "client_terms", "packet", "catalog_seal", "signed"] }
    text url?
    text sealed_hash?
    text pdf_base64? { sensitive = true }
    text filename?
    text as_of?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
    {type: "btree", field: [{name: "salon_id"}, {name: "kind"}]}
  ]
}
