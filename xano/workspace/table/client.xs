table "client" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    int user_id? { table = "user" }
    text ref filters=trim
    text name filters=trim
    email email? filters=trim|lower { sensitive = true }
    bool retained?=false
    bool tombstoned?=false
    json allergens?
    timestamp tombstoned_at?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "ref"}]}
    {type: "btree", field: [{name: "salon_id"}]}
    {type: "btree", field: [{name: "user_id"}]}
  ]
}
