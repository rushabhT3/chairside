function "audit/append" {
  description = """
    Append one row to the hash chain (docs/contracts.md section 3).
    hash = sha256(json_encode({action, actor, payload_hash, prev_hash, ts})) with keys in that order.
    XanoScript has no sorted-key canonical JSON filter and json_encode escapes non-ASCII and "/"
    the PHP way, so the payload_hash is computed by the caller (the agent runtime, whose canonical()
    is unit-tested against docs/hash-vectors.json). When payload_hash is omitted, the payload object
    literal supplied by the Xano caller MUST already be written with keys in alphabetical order and
    contain only ASCII values without "/" (every Xano-side caller in this workspace does that).
    The unique index on prev_hash makes a concurrent double-append fail loudly instead of forking.
  """
  input {
    text event_id
    text actor
    text action
    json payload?
    text payload_hash?
    text ts?
  }
  stack {
    db.query "audit_event" {
      sort = { id: "desc" }
      return = { type: "single" }
    } as $last

    var $prev_hash { value = "0000000000000000000000000000000000000000000000000000000000000000" }
    conditional {
      if ($last != null) {
        var.update $prev_hash { value = $last.hash }
      }
    }

    var $payload_hash { value = $input.payload_hash }
    conditional {
      if ($payload_hash == null || $payload_hash == "") {
        var.update $payload_hash { value = (($input.payload ?? {})|json_encode)|sha256 }
      }
    }

    var $ts { value = $input.ts }
    conditional {
      if ($ts == null || $ts == "") {
        var $stamp { value = now }
        var.update $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }
      }
    }

    var $hash_input {
      value = {
        action: $input.action,
        actor: $input.actor,
        payload_hash: $payload_hash,
        prev_hash: $prev_hash,
        ts: $ts
      }
    }
    var $hash { value = ($hash_input|json_encode)|sha256 }

    db.add "audit_event" {
      data = {
        event_id: $input.event_id,
        prev_hash: $prev_hash,
        hash: $hash,
        actor: $input.actor,
        action: $input.action,
        payload_hash: $payload_hash,
        ts: $ts
      }
    } as $row
  }
  response = $row
  guid = "W_3kBOQBbZJziCYsQcmTIJ1ukBI"
}
