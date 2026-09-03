function "audit/verify" {
  description = "Recompute every hash in audit_event and check each prev_hash links to the previous row (server-side twin of Floor's in-browser Verify)"
  input {
  }
  stack {
    db.query "audit_event" {
      sort = { id: "asc" }
      return = { type: "list" }
    } as $rows

    var $prev { value = "0000000000000000000000000000000000000000000000000000000000000000" }
    var $ok { value = true }
    var $first_bad_index { value = null }
    var $idx { value = 0 }

    foreach ($rows) {
      each as $row {
        var $expected {
          value = ({
            action: $row.action,
            actor: $row.actor,
            payload_hash: $row.payload_hash,
            prev_hash: $row.prev_hash,
            ts: $row.ts
          }|json_encode)|sha256
        }
        conditional {
          if ($row.prev_hash != $prev || $row.hash != $expected) {
            var.update $ok { value = false }
            var.update $first_bad_index { value = $idx }
            break
          }
        }
        var.update $prev { value = $row.hash }
        math.add $idx { value = 1 }
      }
    }
  }
  response = { ok: $ok, checked: $idx, first_bad_index: $first_bad_index, total: ($rows|count) }
  guid = "3i3ZMXiPi0FvY6bPMSb-XhK9IV4"
}
