table "extraction_task" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    enum source { values = ["price_list", "invoice", "intake"] }
    text file
    json fields
    bool needs_review?=false
    enum status?="pending" { values = ["pending", "confirmed", "rejected"] }
    bool quarantined?=false
    json quarantine_reasons?
    int confirmed_by_user_id? { table = "user" }
    timestamp confirmed_at?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "salon_id"}, {name: "needs_review"}]}
    {type: "btree", field: [{name: "quarantined"}]}
  ]
}
