tool "get_consultation_summary" {
  description = "Summarise the latest consultation for a client: state, plan totals, rebook date. Clients see only their own record; staff see any client of their salon."
  instructions = "Use to answer 'what did my last consultation recommend' or to check where a client is in the consultation flow. Pass the client's name or leave it empty for the authenticated user's own record."
  input {
    text client? filters=trim { description = "Client name (staff only); omit to use the authenticated user's own record" }
  }
  stack {
    precondition ($auth.id != null) {
      error_type = "accessdenied"
      error = "Authentication required"
    }

    var $client_row { value = null }
    conditional {
      if ($input.client != null && ($auth.role == "owner" || $auth.role == "stylist")) {
        db.query "client" {
          where = $db.client.salon_id == $auth.salon_id && $db.client.name == $input.client
          return = { type: "single" }
        } as $found
        var.update $client_row { value = $found }
      }
      else {
        db.query "client" {
          where = $db.client.user_id == $auth.id
          return = { type: "single" }
        } as $own
        var.update $client_row { value = $own }
      }
    }

    precondition ($client_row != null) {
      error_type = "notfound"
      error = "Client not found"
    }

    db.query "consultation" {
      where = $db.consultation.client_id == $client_row.id
      sort = { id: "desc" }
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "No consultation yet"
    }

    function.run "snapshot/consultation" {
      input = { ref: $consultation.ref, include_reviews: false }
    } as $projection
  }
  response = {
    consultation_id: $projection.id,
    client: $projection.client.name,
    state: $projection.state,
    stylist: $projection.stylist,
    plan: $projection.plan,
    order: $projection.order,
    booking: $projection.booking
  }
}
