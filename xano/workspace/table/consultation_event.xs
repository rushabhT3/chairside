table "consultation_event" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    text event_id filters=trim
    int salon_id { table = "salon" }
    text consultation_ref?
    text type filters=trim
    json payload?
    text ts
    enum actor?="agent" { values = ["agent", "owner", "stylist", "client", "system"] }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "event_id"}]}
    {type: "btree", field: [{name: "consultation_ref"}, {name: "id", op: "asc"}]}
    {type: "btree", field: [{name: "salon_id"}]}
    {type: "btree", field: [{name: "type"}]}
  ]
  guid = "bdXKGCfBzfaJujpkqy-j_oj47YA"
}
