table "sku" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text code filters=trim
    text name filters=trim
    text brand filters=trim
    int salon_price_cents filters=min:0
    text shade_code?
    enum kind?="retail" { values = ["retail", "backbar", "service"] }
    bool confirmed?=false
    int extraction_task_id? { table = "extraction_task" }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "salon_id"}, {name: "code"}]}
    {type: "btree", field: [{name: "shade_code"}]}
  ]
}
