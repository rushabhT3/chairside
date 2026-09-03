task "price_refresh" {
  description = "Nightly: SKUs whose latest price_snapshot is older than 7 days get a fresh SerpApi google_shopping spread; alert when the salon price deviates more than 15% from the median"
  active = true
  stack {
    var $cutoff { value = now|transform_timestamp:"-7 days" }

    db.query "sku" {
      where = $db.sku.kind != "service"
      sort = { id: "asc" }
      return = { type: "list" }
    } as $skus

    var $refreshed { value = 0 }
    var $alerts { value = [] }

    foreach ($skus) {
      each as $sku {
        db.query "price_snapshot" {
          where = $db.price_snapshot.sku_id == $sku.id
          sort = { id: "desc" }
          return = { type: "single" }
        } as $latest

        conditional {
          if ($latest != null && $latest.as_of_ts >= $cutoff) {
            continue
          }
        }

        try_catch {
          try {
            api.request {
              url = "https://serpapi.com/search"
              method = "GET"
              params = {
                engine: "google_shopping",
                q: $sku.brand ~ " " ~ $sku.name,
                gl: "fr",
                hl: "fr",
                api_key: $env.SERPAPI_API_KEY
              }
              timeout = 30
            } as $serp

            conditional {
              if ($serp.response.status == 200) {
                var $offers { value = $serp.response.result.shopping_results ?? [] }
                var $prices { value = ($offers|map:$$.extracted_price)|filter_null }
                conditional {
                  if (($prices|count) > 0) {
                    var $cents { value = $prices|map:(($$ * 100)|round) }
                    function.run "price/median_cents" {
                      input = { values: $cents }
                    } as $median
                    var $stamp { value = now }
                    var $as_of { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s":"UTC") ~ "Z" }
                    db.add "price_snapshot" {
                      data = {
                        sku_id: $sku.id,
                        min_cents: $cents|min,
                        median_cents: $median,
                        max_cents: $cents|max,
                        source: "google_shopping",
                        as_of: $as_of,
                        as_of_ts: $stamp
                      }
                    } as $snapshot
                    math.add $refreshed { value = 1 }

                    function.run "price/delta_pct" {
                      input = { salon_price_cents: $sku.salon_price_cents, median_cents: $median }
                    } as $delta
                    conditional {
                      if ($delta > 15 || $delta < -15) {
                        var.update $alerts { value = $alerts|push:{ sku_code: $sku.code, delta_pct: $delta } }
                        security.create_uuid as $event_id
                        function.run "events/append_one" {
                          input = {
                            event_id: $event_id,
                            salon_id: $sku.salon_id,
                            consultation_ref: null,
                            type: "price.snapshot",
                            payload: { delta_pct: $delta, median_cents: $median, sku_code: $sku.code },
                            ts: $as_of,
                            actor: "system"
                          }
                        } as $appended
                      }
                    }
                  }
                }
              }
            }
          }
          catch {
            debug.log { value = "price_refresh failed for " ~ $sku.code }
          }
        }
      }
    }

    debug.log { value = "price_refresh: " ~ ($refreshed|to_text) ~ " snapshots, " ~ (($alerts|count)|to_text) ~ " alerts" }
  }
  schedule = [{starts_on: 2026-09-01 02:00:00+0000, freq: 86400}]
  tags = ["serpapi", "prices"]
  guid = "gSzfRrQyQiuPGktQaXm_2wesc5g"
}
