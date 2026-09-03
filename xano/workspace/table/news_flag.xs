table "news_flag" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int sku_id { table = "sku" }
    text consultation_ref?
    text query
    bool clean?=true
    json flags?
    text summary?
    text as_of
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "sku_id"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "consultation_ref"}]}
  ]
  guid = "RVLS8GNRHPTZz72A7rGOtBTfRz0"
}
