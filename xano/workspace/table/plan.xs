table "plan" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref
    json treatment_classes
    int total_cents filters=min:0
    int rebook_weeks?=6
    json facts?
    text prose?
    bool accepted?=false
    timestamp accepted_at?
    timestamp updated_at?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "consultation_ref"}]}
  ]
}
