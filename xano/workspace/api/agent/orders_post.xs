query "orders" verb=POST {
  api_group = "agent"
  description = "Record the retail order for a consultation (orders are recorded, not charged) and attribute it to the stylist and chair"
  auth = "user"
  input {
    text consultation_id
    json items
    int total_cents filters=min:0
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    db.query "consultation" {
      where = $db.consultation.ref == $input.consultation_id && $db.consultation.salon_id == $auth.salon_id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    db.add "order" {
      data = {
        salon_id: $auth.salon_id,
        consultation_ref: $consultation.ref,
        client_id: $consultation.client_id,
        stylist_staff_id: $consultation.stylist_staff_id,
        chair: $consultation.chair,
        items: $input.items,
        total_cents: $input.total_cents,
        currency: "EUR",
        state: "recorded"
      }
    } as $order

    db.edit "consultation" {
      field_name = "id"
      field_value = $consultation.id
      data = { order_id: $order.id, updated_at: now }
    }

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $auth.salon_id,
        consultation_ref: $consultation.ref,
        type: "order.created",
        payload: { chair: $consultation.chair, order_id: $order.id, total_cents: $order.total_cents },
        ts: $ts,
        actor: "agent"
      }
    } as $appended
  }
  response = { id: $order.id, order_id: $order.id, total_cents: $order.total_cents }
}
