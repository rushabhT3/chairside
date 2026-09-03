query "login" verb=POST {
  api_group = "auth"
  description = "Email + password login. Returns a JWT whose extras carry role and salon_id."
  input {
    email email filters=trim|lower
    text password
  }
  stack {
    db.get "user" {
      field_name = "email"
      field_value = $input.email
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Invalid credentials."
    }

    security.check_password {
      text_password = $input.password
      hash_password = $user.password
    } as $is_valid

    precondition ($is_valid) {
      error_type = "accessdenied"
      error = "Invalid credentials."
    }

    precondition ($user.is_active) {
      error_type = "accessdenied"
      error = "Account disabled."
    }

    security.create_auth_token {
      table = "user"
      id = $user.id
      extras = { role: $user.role, salon_id: $user.salon_id }
      expiration = 86400
    } as $authToken
  }
  response = { authToken: $authToken }
  guid = "IE05kUsJ-36brY8Yas07nqNGK8Y"
}
