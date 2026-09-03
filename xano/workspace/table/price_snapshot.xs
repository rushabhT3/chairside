table "price_snapshot" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int sku_id { table = "sku" }
    int min_cents filters=min:0
    int median_cents filters=min:0
    int max_cents filters=min:0
    text source?="google_shopping"
    text as_of
    timestamp as_of_ts?=now
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "sku_id"}, {name: "as_of_ts", op: "desc"}]}
  ]
  guid = "s0YniADTdouxHxwjRgQqJxijZ90"
}
