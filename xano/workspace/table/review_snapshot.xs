table "review_snapshot" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    text competitor_place_id
    text competitor_name?
    text summary
    json quotes?
    text as_of
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
    {type: "btree", field: [{name: "salon_id"}]}
  ]
}
