table "product_identity" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref?
    int sku_id? { table = "sku" }
    json lens
    text as_of
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
    {type: "btree", field: [{name: "sku_id"}]}
  ]
}
