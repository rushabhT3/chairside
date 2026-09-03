table "staff" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    int user_id { table = "user" }
    text name filters=trim
    enum role { values = ["owner", "stylist"] }
    int chair?
    bool is_active?=true
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "salon_id"}]}
    {type: "btree|unique", field: [{name: "user_id"}]}
  ]
}
