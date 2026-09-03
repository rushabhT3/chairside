table "user" {
  auth = true
  schema {
    int id
    timestamp created_at?=now
    text name filters=trim
    email email filters=trim|lower { sensitive = true }
    password password { sensitive = true }
    enum role?="client" { values = ["owner", "stylist", "client", "agent"] }
    int salon_id? { table = "salon" }
    bool is_active?=true
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "email"}]}
    {type: "btree", field: [{name: "salon_id"}]}
    {type: "btree", field: [{name: "role"}]}
  ]
}
