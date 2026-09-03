table "audit_event" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    text event_id
    text prev_hash
    text hash
    enum actor { values = ["agent", "owner", "stylist", "client", "system"] }
    text action
    text payload_hash
    text ts
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "hash"}]}
    {type: "btree|unique", field: [{name: "prev_hash"}]}
    {type: "btree|unique", field: [{name: "event_id"}]}
  ]
  guid = "628GwmoNvqvuaJ7Ps6jJbw63jU8"
}
