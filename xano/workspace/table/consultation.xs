table "consultation" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    text ref filters=trim
    int salon_id { table = "salon" }
    int client_id { table = "client" }
    int stylist_staff_id? { table = "staff" }
    int chair?
    enum state?="capture" { values = ["capture", "color_tones", "skin_hd", "hair_diagnostics", "face_attributes", "plan", "simulations", "price", "consent", "commit", "done", "needs_attention"] }
    text failing_step?
    bool consent_ready?=false
    int plan_id? { table = "plan" }
    int order_id? { table = "order" }
    int booking_id? { table = "booking" }
    timestamp started_at?=now
    timestamp updated_at?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "ref"}]}
    {type: "btree", field: [{name: "salon_id"}, {name: "started_at", op: "desc"}]}
    {type: "btree", field: [{name: "client_id"}]}
    {type: "btree", field: [{name: "state"}]}
  ]
}
