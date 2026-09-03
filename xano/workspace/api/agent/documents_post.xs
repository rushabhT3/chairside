query "documents" verb=POST {
  api_group = "agent"
  description = "Register a generated or sealed document. pdf_base64 is what the Commit Service hands to eSign; it is stored sensitive and never returned by read endpoints."
  auth = "user"
  input {
    enum kind { values = ["platform_agreement", "consent", "intake", "aftercare", "price_list", "client_terms", "packet", "catalog_seal", "signed"] }
    text url?
    text sealed_hash?
    text pdf_base64? { sensitive = true }
    text filename?
    text consultation_id?
    text as_of?
  }
  stack {
    function.run "rbac/require_agent" {
      input = { role: $auth.role }
    } as $allowed

    db.add "document" {
      data = {
        salon_id: $auth.salon_id,
        consultation_ref: $input.consultation_id,
        kind: $input.kind,
        url: $input.url,
        sealed_hash: $input.sealed_hash,
        pdf_base64: $input.pdf_base64,
        filename: $input.filename,
        as_of: $input.as_of
      }
    } as $document
  }
  response = { document_id: $document.id, kind: $document.kind, sealed_hash: $document.sealed_hash }
}
