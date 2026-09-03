function "snapshot/consultation" {
  description = "Project one consultation (events, scan, plan, simulations, prices, news, staff-only reviews, consent, order, booking) into the web Consultation shape from web/src/lib/snapshot.ts"
  input {
    text ref
    bool include_reviews?=false
  }
  stack {
    db.query "consultation" {
      where = $db.consultation.ref == $input.ref
      return = { type: "single" }
    } as $consultation

    precondition ($consultation != null) {
      error_type = "notfound"
      error = "consultation_not_found"
    }

    db.get "client" {
      field_name = "id"
      field_value = $consultation.client_id
    } as $client

    var $stylist_name { value = "" }
    conditional {
      if ($consultation.stylist_staff_id != null) {
        db.get "staff" {
          field_name = "id"
          field_value = $consultation.stylist_staff_id
        } as $staff
        var.update $stylist_name { value = $staff.name }
      }
    }

    db.query "consultation_event" {
      where = $db.consultation_event.consultation_ref == $input.ref
      sort = { id: "asc" }
      return = { type: "list" }
    } as $event_rows

    var $events {
      value = $event_rows|map:{
        id: $$.event_id,
        consultation_id: $$.consultation_ref,
        salon_id: ($$.salon_id|to_text),
        type: $$.type,
        payload: $$.payload,
        ts: $$.ts,
        actor: $$.actor
      }
    }

    db.query "scan" {
      where = $db.scan.consultation_ref == $input.ref && $db.scan.deleted == false
      sort = { id: "desc" }
      return = { type: "single" }
    } as $scan_row

    var $scan { value = null }
    conditional {
      if ($scan_row != null) {
        var.update $scan {
          value = {
            scan_id: $scan_row.ref,
            ts: $scan_row.as_of,
            color_tones: $scan_row.color_tones,
            skin: $scan_row.scores,
            hair: $scan_row.hair,
            face: $scan_row.face
          }
        }
      }
    }

    var $previous_scan { value = null }
    conditional {
      if ($scan_row != null) {
        db.query "scan" {
          where = $db.scan.client_id == $consultation.client_id && $db.scan.id < $scan_row.id && $db.scan.retained == true && $db.scan.deleted == false
          sort = { id: "desc" }
          return = { type: "single" }
        } as $prev_row
        conditional {
          if ($prev_row != null) {
            var.update $previous_scan {
              value = {
                scan_id: $prev_row.ref,
                ts: $prev_row.as_of,
                color_tones: $prev_row.color_tones,
                skin: $prev_row.scores,
                hair: $prev_row.hair,
                face: $prev_row.face
              }
            }
          }
        }
      }
    }

    db.query "plan" {
      where = $db.plan.consultation_ref == $input.ref
      return = { type: "single" }
    } as $plan_row

    var $plan { value = null }
    conditional {
      if ($plan_row != null) {
        db.query "plan_item" {
          where = $db.plan_item.plan_id == $plan_row.id
          sort = { id: "asc" }
          return = { type: "list" }
        } as $items
        var.update $plan {
          value = {
            treatment_classes: $plan_row.treatment_classes,
            services: ($items|filter:$$.kind == "service")|map:{ code: $$.code, name: $$.name, price_cents: $$.price_cents, qty: $$.qty, treatment_class: $$.treatment_class },
            products: ($items|filter:$$.kind == "product")|map:{ code: $$.code, name: $$.name, price_cents: $$.price_cents, qty: $$.qty, treatment_class: $$.treatment_class },
            total_cents: $plan_row.total_cents,
            rebook_weeks: $plan_row.rebook_weeks,
            facts: $plan_row.facts ?? [],
            prose: $plan_row.prose ?? ""
          }
        }
      }
    }

    db.query "simulation" {
      where = $db.simulation.consultation_ref == $input.ref
      sort = { id: "asc" }
      return = { type: "list" }
    } as $sim_rows
    var $simulations {
      value = $sim_rows|map:{
        tool: $$.tool,
        server: $$.server,
        tab: $$.tab,
        sku_code: $$.sku_code,
        hex: $$.hex,
        label: $$.label,
        before_url: $$.before_url,
        after_url: $$.after_url,
        as_of: $$.as_of
      }
    }

    db.query "product_identity" {
      where = $db.product_identity.consultation_ref == $input.ref
      return = { type: "list" }
    } as $identities
    var $prices { value = [] }
    foreach ($identities) {
      each as $identity {
        conditional {
          if ($identity.sku_id != null) {
            db.get "sku" {
              field_name = "id"
              field_value = $identity.sku_id
            } as $sku
            db.query "price_snapshot" {
              where = $db.price_snapshot.sku_id == $identity.sku_id
              sort = { id: "desc" }
              return = { type: "single" }
            } as $snapshot
            conditional {
              if ($snapshot != null) {
                function.run "price/delta_pct" {
                  input = { salon_price_cents: $sku.salon_price_cents, median_cents: $snapshot.median_cents }
                } as $delta
                var $action { value = "match" }
                var $reason { value = "salon price within 5% of the market median" }
                conditional {
                  if ($delta > 15) {
                    var.update $action { value = "bundle" }
                    var.update $reason { value = "salon price is " ~ ($delta|to_text) ~ "% above the market median; bundle with the service" }
                  }
                  elseif ($delta < -15) {
                    var.update $action { value = "hold" }
                    var.update $reason { value = "salon price is " ~ ((0 - $delta)|to_text) ~ "% below the market median; hold and review" }
                  }
                  elseif ($delta > 5) {
                    var.update $action { value = "match" }
                    var.update $reason { value = "salon price is " ~ ($delta|to_text) ~ "% above median; match the market" }
                  }
                }
                var.update $prices {
                  value = $prices|push:{
                    sku_code: $sku.code,
                    name: $sku.name,
                    salon_price_cents: $sku.salon_price_cents,
                    min_cents: $snapshot.min_cents,
                    median_cents: $snapshot.median_cents,
                    max_cents: $snapshot.max_cents,
                    as_of: $snapshot.as_of,
                    action: $action,
                    reason: $reason
                  }
                }
              }
            }
          }
        }
      }
    }

    db.query "news_flag" {
      where = $db.news_flag.consultation_ref == $input.ref
      sort = { id: "desc" }
      return = { type: "single" }
    } as $news_row
    var $news { value = null }
    conditional {
      if ($news_row != null) {
        var.update $news {
          value = { query: $news_row.query, clean: $news_row.clean, flags: $news_row.flags ?? [], as_of: $news_row.as_of }
        }
      }
    }

    var $reviews { value = [] }
    conditional {
      if ($input.include_reviews) {
        db.query "review_snapshot" {
          where = $db.review_snapshot.consultation_ref == $input.ref
          return = { type: "list" }
        } as $review_rows
        var.update $reviews {
          value = $review_rows|map:{
            place_id: $$.competitor_place_id,
            competitor: $$.competitor_name,
            summary: $$.summary,
            quotes: $$.quotes ?? [],
            as_of: $$.as_of
          }
        }
      }
    }

    db.query "envelope" {
      where = $db.envelope.consultation_ref == $input.ref && $db.envelope.kind == "consent"
      sort = { id: "desc" }
      return = { type: "single" }
    } as $envelope_row
    var $consent { value = null }
    conditional {
      if ($envelope_row != null && $plan_row != null) {
        var $sealed_hash { value = null }
        conditional {
          if ($envelope_row.signed_document_id != null) {
            db.get "document" {
              field_name = "id"
              field_value = $envelope_row.signed_document_id
            } as $signed_document
            var.update $sealed_hash { value = $signed_document.sealed_hash }
          }
        }
        var.update $consent {
          value = {
            template_id: "consent",
            treatment_classes: $plan_row.treatment_classes,
            envelope: {
              envelope_id: ($envelope_row.id|to_text),
              state: $envelope_row.state,
              session_url: $envelope_row.session_url,
              expires_at: $envelope_row.expires_at,
              sealed_hash: $sealed_hash
            }
          }
        }
      }
    }

    var $order { value = null }
    conditional {
      if ($consultation.order_id != null) {
        db.get "order" {
          field_name = "id"
          field_value = $consultation.order_id
        } as $order_row
        var.update $order {
          value = { id: ($order_row.id|to_text), total_cents: $order_row.total_cents, items: $order_row.items }
        }
      }
    }

    var $booking { value = null }
    conditional {
      if ($consultation.booking_id != null) {
        db.get "booking" {
          field_name = "id"
          field_value = $consultation.booking_id
        } as $booking_row
        var.update $booking {
          value = { id: ($booking_row.id|to_text), when: $booking_row.when_at, service: $booking_row.service }
        }
      }
    }
  }
  response = {
    id: $consultation.ref,
    client: { id: $client.ref, name: $client.name },
    stylist: $stylist_name,
    chair: $consultation.chair,
    state: $consultation.state,
    failing_step: $consultation.failing_step,
    started_at: $consultation.started_at,
    events: $events,
    scan: $scan,
    previous_scan: $previous_scan,
    plan: $plan,
    simulations: $simulations,
    prices: $prices,
    news: $news,
    reviews: $reviews,
    consent: $consent,
    order: $order,
    booking: $booking
  }
}
