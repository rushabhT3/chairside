function "snapshot/build" {
  description = "Assemble the full web Snapshot (web/src/lib/snapshot.ts) for one salon: chairs today, consultations, ledger, extraction queue, onboarding log, price watch, attribution, cost, quarantine"
  input {
    int salon_id { table = "salon" }
    bool include_reviews?=false
  }
  stack {
    db.get "salon" {
      field_name = "id"
      field_value = $input.salon_id
    } as $salon_row

    precondition ($salon_row != null) {
      error_type = "notfound"
      error = "salon_not_found"
    }

    db.query "staff" {
      where = $db.staff.salon_id == $input.salon_id && $db.staff.is_active == true
      sort = { id: "asc" }
      return = { type: "list" }
    } as $staff_rows

    db.query "staff" {
      where = $db.staff.salon_id == $input.salon_id && $db.staff.role == "owner"
      return = { type: "single" }
    } as $owner_row

    db.get "user" {
      field_name = "id"
      field_value = $owner_row.user_id
    } as $owner_user

    var $stylists { value = [] }
    foreach ($staff_rows|filter:$$.role == "stylist") {
      each as $stylist {
        db.get "user" {
          field_name = "id"
          field_value = $stylist.user_id
        } as $stylist_user
        var.update $stylists { value = $stylists|push:{ name: $stylist.name, email: $stylist_user.email } }
      }
    }

    var $salon {
      value = {
        id: ($salon_row.id|to_text),
        name: $salon_row.name,
        address: $salon_row.address,
        city: $salon_row.city,
        postcode: $salon_row.postcode,
        country: $salon_row.country,
        jurisdiction: $salon_row.jurisdiction,
        domain: $salon_row.domain ?? "",
        owner: { name: $owner_row.name, email: $owner_user.email },
        stylists: $stylists,
        chairs: $salon_row.chairs,
        color_line: $salon_row.color_line
      }
    }

    db.query "shade_map" {
      where = $db.shade_map.salon_id == $input.salon_id
      sort = { code: "asc" }
      return = { type: "list" }
    } as $shade_rows
    var $shade_map { value = $shade_rows|map:{ line: $$.line, code: $$.code, name: $$.name, hex: $$.hex, undertone: $$.undertone, level: $$.level } }

    db.query "sku" {
      where = $db.sku.salon_id == $input.salon_id
      sort = { code: "asc" }
      return = { type: "list" }
    } as $sku_rows
    var $skus { value = $sku_rows|map:{ code: $$.code, name: $$.name, brand: $$.brand, salon_price_cents: $$.salon_price_cents, shade_code: $$.shade_code, kind: $$.kind } }

    var $today_start { value = now|transform_timestamp:"-24 hours" }
    db.query "consultation" {
      where = $db.consultation.salon_id == $input.salon_id && $db.consultation.started_at >= $today_start
      sort = { started_at: "asc" }
      return = { type: "list" }
    } as $today_rows

    var $chairs { value = [] }
    var $consultations { value = {} }
    foreach ($today_rows) {
      each as $row {
        function.run "snapshot/consultation" {
          input = { ref: $row.ref, include_reviews: $input.include_reviews }
        } as $projection
        var.update $consultations { value = $consultations|set:$row.ref:$projection }
        var.update $chairs {
          value = $chairs|push:{
            chair: $row.chair,
            stylist: $projection.stylist,
            client: $projection.client,
            consultation_id: $row.ref,
            state: $row.state,
            time: ($row.started_at|format_timestamp:"H:i":"Europe/Paris")
          }
        }
      }
    }

    db.query "audit_event" {
      sort = { id: "asc" }
      return = { type: "list" }
    } as $audit_rows
    var $audit { value = $audit_rows|map:{ id: $$.event_id, prev_hash: $$.prev_hash, hash: $$.hash, actor: $$.actor, action: $$.action, payload_hash: $$.payload_hash, ts: $$.ts } }

    db.query "extraction_task" {
      where = $db.extraction_task.salon_id == $input.salon_id
      sort = { id: "asc" }
      return = { type: "list" }
    } as $extraction_rows
    var $extractions {
      value = ($extraction_rows|filter:$$.quarantined == false)|map:{
        id: ($$.id|to_text),
        source: $$.source,
        file: $$.file,
        needs_review: $$.needs_review,
        status: $$.status,
        fields: $$.fields
      }
    }
    var $quarantine {
      value = ($extraction_rows|filter:$$.quarantined == true)|map:{
        id: ($$.id|to_text),
        source: $$.source,
        file: $$.file,
        reasons: $$.quarantine_reasons ?? [],
        ts: $$.created_at
      }
    }

    db.query "onboarding" {
      where = $db.onboarding.salon_id == $input.salon_id
      return = { type: "single" }
    } as $onboarding_row
    var $onboarding { value = [] }
    conditional {
      if ($onboarding_row != null) {
        var.update $onboarding { value = $onboarding_row.steps ?? [] }
      }
    }

    var $price_watch { value = [] }
    foreach ($sku_rows) {
      each as $sku {
        db.query "price_snapshot" {
          where = $db.price_snapshot.sku_id == $sku.id
          sort = { id: "desc" }
          return = { type: "single" }
        } as $snapshot
        conditional {
          if ($snapshot != null && $snapshot.median_cents > 0) {
            function.run "price/delta_pct" {
              input = { salon_price_cents: $sku.salon_price_cents, median_cents: $snapshot.median_cents }
            } as $delta
            var.update $price_watch {
              value = $price_watch|push:{
                sku_code: $sku.code,
                name: $sku.name,
                salon_price_cents: $sku.salon_price_cents,
                median_cents: $snapshot.median_cents,
                delta_pct: $delta,
                alert: ($delta > 15 || $delta < -15),
                as_of: $snapshot.as_of
              }
            }
          }
        }
      }
    }

    var $attribution { value = [] }
    foreach ($staff_rows) {
      each as $member {
        db.query "consultation" {
          where = $db.consultation.stylist_staff_id == $member.id
          return = { type: "count" }
        } as $consultation_count
        db.query "order" {
          where = $db.order.stylist_staff_id == $member.id && $db.order.state == "recorded"
          return = { type: "list" }
        } as $orders
        var.update $attribution {
          value = $attribution|push:{
            stylist: $member.name,
            chair: $member.chair,
            consultations: $consultation_count,
            orders: ($orders|count),
            revenue_cents: (($orders|map:$$.total_cents)|sum)
          }
        }
      }
    }

    db.query "consultation_event" {
      where = $db.consultation_event.salon_id == $input.salon_id && $db.consultation_event.type == "tool.called"
      return = { type: "list" }
    } as $tool_calls
    var $servers { value = ["mcp/beauty", "mcp/fashion", "mcp/foxit", "rest/serpapi", "rest/namecom", "rest/doctavian", "rest/nutrient", "commit/xano"] }
    var $per_consultation { value = [] }
    var $per_onboarding { value = [] }
    var $consultation_total { value = $today_rows|count }
    foreach ($servers) {
      each as $server {
        var $calls { value = $tool_calls|filter:$$.payload.server == $server }
        var $with_consultation { value = $calls|filter:$$.consultation_ref != null }
        var $without_consultation { value = $calls|filter:$$.consultation_ref == null }
        var $units_consultation { value = (($with_consultation|map:$$.payload.units)|sum) }
        var $units_onboarding { value = (($without_consultation|map:$$.payload.units)|sum) }
        conditional {
          if ($consultation_total > 0) {
            var.update $units_consultation { value = ($units_consultation / $consultation_total)|round }
          }
        }
        var.update $per_consultation { value = $per_consultation|push:{ vendor: $server, unit: "units", count: $units_consultation } }
        var.update $per_onboarding { value = $per_onboarding|push:{ vendor: $server, unit: "units", count: $units_onboarding } }
      }
    }
    var $weekly_refresh {
      value = [{ vendor: "rest/serpapi", unit: "searches", count: ($price_watch|count) }]
    }
  }
  response = {
    generated_at: now,
    salon: $salon,
    shade_map: $shade_map,
    skus: $skus,
    chairs: $chairs,
    consultations: $consultations,
    audit: $audit,
    extractions: $extractions,
    onboarding: $onboarding,
    price_watch: $price_watch,
    attribution: $attribution,
    cost: { per_consultation: $per_consultation, per_onboarding: $per_onboarding, weekly_refresh: $weekly_refresh },
    quarantine: $quarantine
  }
  guid = "ZrddCafIA9zrHsQ7fHv_g6G3KZQ"
}
