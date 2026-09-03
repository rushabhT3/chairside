query "signup" verb=POST {
  api_group = "auth"
  description = "Create an owner, stylist or client account. The agent role is never self-issued: it is created from the Xano dashboard (xano/README.md)."
  input {
    text name filters=trim|min:1
    email email filters=trim|lower
    text password filters=min:8|max:128
    enum role?="client" { values = ["owner", "stylist", "client"] }
    int salon_id? { table = "salon" }
  }
  stack {
    db.get "user" {
      field_name = "email"
      field_value = $input.email
    } as $existing

    precondition ($existing == null) {
      error_type = "accessdenied"
      error = "This account is already in use."
    }

    db.add "user" {
      data = {
        name: $input.name,
        email: $input.email,
        password: $input.password,
        role: $input.role,
        salon_id: $input.salon_id
      }
    } as $user

    security.create_auth_token {
      table = "user"
      id = $user.id
      extras = { role: $user.role, salon_id: $user.salon_id }
      expiration = 86400
    } as $authToken
  }
  response = { authToken: $authToken }
}
