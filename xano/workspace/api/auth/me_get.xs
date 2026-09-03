query "me" verb=GET {
  api_group = "auth"
  description = "The authenticated user without the password hash"
  auth = "user"
  input {
  }
  stack {
    db.get "user" {
      field_name = "id"
      field_value = $auth.id
    } as $user
  }
  response = { id: $user.id, name: $user.name, email: $user.email, role: $user.role, salon_id: $user.salon_id }
  guid = "Jf31CqUof-MMZpI6rPKZx1A5WUk"
}
