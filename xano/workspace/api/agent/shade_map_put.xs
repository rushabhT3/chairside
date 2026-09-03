query "shade_map" verb=PUT {
  api_group = "agent"
  description = "Seed or replace the salon's shade table from the color line (upsert by line + code)"
  auth = "user"
  input {
    json entries
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    var $written { value = 0 }
    foreach ($input.entries) {
      each as $entry {
        db.query "shade_map" {
          where = $db.shade_map.salon_id == $auth.salon_id && $db.shade_map.line == $entry.line && $db.shade_map.code == $entry.code
          return = { type: "single" }
        } as $existing
        conditional {
          if ($existing == null) {
            db.add "shade_map" {
              data = { salon_id: $auth.salon_id, line: $entry.line, code: $entry.code, name: $entry.name, hex: $entry.hex, undertone: $entry.undertone, level: $entry.level }
            }
          }
          else {
            db.edit "shade_map" {
              field_name = "id"
              field_value = $existing.id
              data = { name: $entry.name, hex: $entry.hex, undertone: $entry.undertone, level: $entry.level }
            }
          }
        }
        math.add $written { value = 1 }
      }
    }
  }
  response = { written: $written }
  guid = "wxHMU3lsoAxEdDHSBUgWUx2CwbY"
}
