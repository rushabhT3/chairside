query "bookings" verb=POST {
  api_group = "agent"
  description = "Rebook the client after a consultation (default six weeks out)"
  auth = "user"
  input {
    text consultation_id
    timestamp when
    text service filters=trim
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.extras.role }
    } as $allowed

    db.query "consultation" {
      where = $db.consultation.ref == $input.consultation_id && $db.consultation.salon_id == $auth.extras.salon_id
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    db.add "booking" {
      data = {
        salon_id: $auth.extras.salon_id,
        consultation_ref: $consultation.ref,
        client_id: $consultation.client_id,
        stylist_staff_id: $consultation.stylist_staff_id,
        chair: $consultation.chair,
        service: $input.service,
        when_at: $input.when,
        source: "floor",
        state: "booked"
      }
    } as $booking

    db.edit "consultation" {
      field_name = "id"
      field_value = $consultation.id
      data = { booking_id: $booking.id, updated_at: now }
    }

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }

    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $auth.extras.salon_id,
        consultation_ref: $consultation.ref,
        type: "booking.created",
        payload: { booking_id: $booking.id, chair: $consultation.chair, service: $input.service, source: "floor" },
        ts: $ts,
        actor: "agent"
      }
    } as $appended
  }
  response = { id: $booking.id, booking_id: $booking.id, when: $booking.when_at, service: $booking.service }
  guid = "_IY-v5IGSNbtUn2FJTTHTEFhJ1o"
}
