table "order" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref
    int client_id { table = "client" }
    int stylist_staff_id? { table = "staff" }
    int chair?
    json items
    int total_cents filters=min:0
    text currency?="EUR"
    enum state?="recorded" { values = ["recorded", "cancelled"] }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
    {type: "btree", field: [{name: "salon_id"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "stylist_staff_id"}]}
  ]
}
