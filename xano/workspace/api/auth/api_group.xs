api_group "auth" {
  canonical = "chairside-auth"
  description = "Signup, login, me. JWT extras carry role and salon_id so every other group can gate on $auth.role."
  tags = ["auth"]
}
