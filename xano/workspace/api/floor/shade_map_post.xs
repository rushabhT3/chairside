query "shade_map" verb=POST {
  api_group = "floor"
  description = "Add a shade to the salon's line (owner only)"
  auth = "user"
  input {
    text line filters=trim
    text code filters=trim
    text name filters=trim
    text hex filters=trim|lower|min:7|max:7
    enum undertone { values = ["warm", "cool", "neutral"] }
    int level filters=min:1|max:10
  }
  stack {
    precondition ($auth.extras.role == "owner") {
      error_type = "accessdenied"
      error = "role_not_allowed"
    }

    db.add "shade_map" {
      data = {
        salon_id: $auth.extras.salon_id,
        line: $input.line,
        code: $input.code,
        name: $input.name,
        hex: $input.hex,
        undertone: $input.undertone,
        level: $input.level
      }
    } as $entry
  }
  response = $entry
  guid = "Dyzz_2mZF3s4bBd6TMcPvuWMVGc"
}
