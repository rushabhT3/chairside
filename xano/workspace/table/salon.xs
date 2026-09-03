table "salon" {
  auth = false
  schema {
    int id
    timestamp created_at?=now
    text name filters=trim
    text address filters=trim
    text city filters=trim
    text postcode filters=trim
    text country?="FR"
    enum jurisdiction?="FR" { values = ["FR", "US"] }
    text color_line?="Majirel"
    int chairs?=3
    text domain?
    int owner_user_id? { table = "user" }
    json settings?
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "owner_user_id"}]}
  ]
  guid = "5tIopuVZ-ilKHR_GYjP3ie56Jzk"
}
