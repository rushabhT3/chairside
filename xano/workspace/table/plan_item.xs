table "plan_item" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int plan_id { table = "plan" }
    enum kind { values = ["service", "product"] }
    text code
    text name
    int price_cents filters=min:0
    int qty?=1 filters=min:1
    enum treatment_class?="none" { values = ["chemical", "heat", "injectable", "laser", "none"] }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "plan_id"}]}
  ]
  guid = "mnnkJjX8yfKN2eJoG99Cz3IrEMY"
}
