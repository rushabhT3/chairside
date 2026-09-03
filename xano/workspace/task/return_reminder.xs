task "return_reminder" {
  description = "Daily: bookings due within the next day that have not been reminded get a booking.created reminder event (the salon's own channel sends the message); rebook date is six weeks after the last consultation"
  active = true
  stack {
    var $window_end { value = now|transform_timestamp:"+1 day" }

    db.query "booking" {
      where = $db.booking.state == "booked" && $db.booking.reminder_sent == false && $db.booking.when_at <= $window_end && $db.booking.when_at >= now
      sort = { when_at: "asc" }
      return = { type: "list" }
    } as $due

    foreach ($due) {
      each as $booking {
        db.edit "booking" {
          field_name = "id"
          field_value = $booking.id
          data = { reminder_sent: true, state: "reminded" }
        }

        security.create_uuid as $event_id
        var $stamp { value = now }
        var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }
        function.run "events/append_one" {
          input = {
            event_id: $event_id,
            salon_id: $booking.salon_id,
            consultation_ref: $booking.consultation_ref,
            type: "booking.created",
            payload: { booking_id: $booking.id, reminder: true, service: $booking.service },
            ts: $ts,
            actor: "system"
          }
        } as $appended
      }
    }
  }
  schedule = [{starts_on: 2026-09-01 07:00:00+0000, freq: 86400}]
  tags = ["bookings", "retention"]
}
