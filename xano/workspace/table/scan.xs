table "scan" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    text ref filters=trim
    int salon_id { table = "salon" }
    int client_id { table = "client" }
    text consultation_ref?
    json scores?
    json color_tones?
    json hair?
    json face?
    attachment image?
    text image_sha256?
    bool retained?=false
    bool deleted?=false
    text as_of?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "ref"}]}
    {type: "btree", field: [{name: "client_id"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
  ]
  guid = "AQ-fZSxQz3eSWqmkt7kO-DvI9H0"
}
