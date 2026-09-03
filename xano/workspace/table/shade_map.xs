table "shade_map" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text line filters=trim
    text code filters=trim
    text name filters=trim
    text hex filters=trim|lower
    enum undertone { values = ["warm", "cool", "neutral"] }
    int level filters=min:1|max:10
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "salon_id"}, {name: "line"}, {name: "code"}]}
  ]
}
