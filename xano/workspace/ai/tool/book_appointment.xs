tool "book_appointment" {
  description = "Book a chair at a salon from any MCP client; the booking lands on Floor attributed to the authenticated user"
  instructions = "Book an appointment. Give the salon name, the service (for example 'colour', 'cut', 'skin consultation') and an ISO-8601 date-time. Returns the booking id and the chair."
  input {
    text salon filters=trim { description = "Salon name, e.g. Atelier Noor" }
    text service filters=trim { description = "Service to book" }
    timestamp when { description = "ISO-8601 date-time for the appointment" }
  }
  stack {
    precondition ($auth.id != null) {
      error_type = "accessdenied"
      error = "Authentication required"
    }

    db.query "salon" {
      where = $db.salon.name == $input.salon
      return = { type: "single" }
    } as $salon

    precondition ($salon != null) {
      error_type = "notfound"
      error = "Salon not found"
    }

    db.query "client" {
      where = $db.client.user_id == $auth.id && $db.client.salon_id == $salon.id
      return = { type: "single" }
    } as $client

    conditional {
      if ($client == null) {
        db.get "user" {
          field_name = "id"
          field_value = $auth.id
        } as $user
        security.create_uuid as $ref
        db.add "client" {
          data = { salon_id: $salon.id, user_id: $auth.id, ref: $ref, name: $user.name, email: $user.email, retained: false }
        } as $client
      }
    }

    db.query "booking" {
      where = $db.booking.salon_id == $salon.id && $db.booking.when_at == $input.when && $db.booking.state != "cancelled"
      return = { type: "list" }
    } as $same_slot

    var $chair { value = ($same_slot|count) + 1 }

    precondition ($chair <= $salon.chairs) {
      error_type = "standard"
      error = "No chair free at that time"
    }

    db.add "booking" {
      data = {
        salon_id: $salon.id,
        client_id: $client.id,
        chair: $chair,
        service: $input.service,
        when_at: $input.when,
        source: "mcp",
        source_identity: $auth.id|to_text,
        state: "booked"
      }
    } as $booking

    security.create_uuid as $event_id
    var $stamp { value = now }
    var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }
    function.run "events/append_one" {
      input = {
        event_id: $event_id,
        salon_id: $salon.id,
        consultation_ref: null,
        type: "booking.created",
        payload: { booking_id: $booking.id, chair: $chair, service: $input.service, source: "mcp" },
        ts: $ts,
        actor: "client"
      }
    } as $appended
  }
  response = { booking_id: $booking.id, salon: $salon.name, chair: $chair, service: $booking.service, when: $booking.when_at }
}
