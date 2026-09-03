table "onboarding" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    json steps?
    bool docs_reviewed?=false
    enum state?="running" { values = ["running", "done", "needs_attention"] }
    text failing_step?
    timestamp updated_at?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "salon_id"}]}
  ]
  guid = "3hEd8cY4cptNwJiCttk36jAs_d0"
}
