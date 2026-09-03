task "envelope_poll" {
  description = "Every 2 minutes: envelopes in sent are polled at Foxit eSign (status checks are free); once the folder is completed the signed document is downloaded, stored, and envelope.signed is appended to the ledger"
  active = true
  stack {
    db.query "envelope" {
      where = $db.envelope.state == "sent" && $db.envelope.provider_id != null
      sort = { id: "asc" }
      return = { type: "list" }
    } as $envelopes

    foreach ($envelopes) {
      each as $envelope {
        try_catch {
          try {
            function.run "esign/get_folder" {
              input = { folder_id: $envelope.provider_id }
            } as $folder

            var $status { value = ($folder.folder.folderStatus ?? $folder.folderStatus ?? "")|to_upper }

            conditional {
              if ($status == "COMPLETED" || $status == "EXECUTED") {
                function.run "esign/download_folder" {
                  input = { folder_id: $envelope.provider_id }
                } as $signed_body

                var $sealed_hash { value = ($signed_body|json_encode)|sha256 }

                db.add "document" {
                  data = {
                    salon_id: $envelope.salon_id,
                    consultation_ref: $envelope.consultation_ref,
                    kind: "signed",
                    url: $env.FOXIT_ESIGN_BASE_URL ~ "/api/folders/downloadfolder?folderId=" ~ $envelope.provider_id,
                    sealed_hash: $sealed_hash,
                    filename: "signed-" ~ ($envelope.id|to_text) ~ ".pdf",
                    as_of: now
                  }
                } as $signed_document

                db.edit "envelope" {
                  field_name = "id"
                  field_value = $envelope.id
                  data = { state: "signed", signed_at: now, signed_document_id: $signed_document.id, session_url: null }
                }

                security.create_uuid as $event_id
                var $stamp { value = now }
                var $ts { value = ($stamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($stamp|format_timestamp:"H:i:s.v":"UTC") ~ "Z" }
                function.run "events/append_one" {
                  input = {
                    event_id: $event_id,
                    salon_id: $envelope.salon_id,
                    consultation_ref: $envelope.consultation_ref,
                    type: "envelope.signed",
                    payload: { envelope_id: $envelope.id, kind: $envelope.kind, sealed_hash: $sealed_hash, signed_document_id: $signed_document.id },
                    ts: $ts,
                    actor: "system"
                  }
                } as $appended
              }
              elseif ($envelope.expires_at != null && $envelope.expires_at < now) {
                db.edit "envelope" {
                  field_name = "id"
                  field_value = $envelope.id
                  data = { state: "expired" }
                }
              }
            }
          }
          catch {
            debug.log { value = "envelope_poll failed for envelope " ~ ($envelope.id|to_text) }
          }
        }
      }
    }
  }
  schedule = [{starts_on: 2026-09-01 00:00:00+0000, freq: 120}]
  tags = ["esign", "envelopes"]
}
