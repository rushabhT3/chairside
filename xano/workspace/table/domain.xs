table "domain" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    int salon_id { table = "salon" }
    text domain_name filters=trim|lower
    text registrar?="name.com"
    text order_id?
    text expire_date?
    json dns_records?
    json forwarding?
    text as_of?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "domain_name"}]}
    {type: "btree", field: [{name: "salon_id"}]}
  ]
}
