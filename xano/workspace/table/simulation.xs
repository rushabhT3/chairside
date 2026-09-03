table "simulation" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text consultation_ref
    text tool
    text server
    enum tab?="hair" { values = ["hair", "skin", "style"] }
    text sku_code?
    text hex?
    text label?
    text before_url?
    text after_url?
    text image_ref?
    text as_of
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
  ]
  guid = "esv2o1AlUU3fJ6d02z6qVbFQh80"
}
