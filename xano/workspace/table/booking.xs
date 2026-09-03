table "booking" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    int client_id { table = "client" }
    int stylist_staff_id? { table = "staff" }
    int chair?
    text service
    timestamp when_at
    enum source?="floor" { values = ["floor", "mirror", "mcp", "task"] }
    text source_identity?
    enum state?="booked" { values = ["booked", "reminded", "cancelled", "done"] }
    bool reminder_sent?=false
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "salon_id"}, {name: "when_at", op: "asc"}]}
    {type: "btree", field: [{name: "client_id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
  ]
  guid = "HwXVt8AiPtinQ8yEEPJDAGKgTk0"
}
