# Seed data: Atelier Noor

Everything the fixtures-mode demo needs to open a salon and run consultations. Shapes are defined in `docs/contracts.md` section 6.

| File | What it is |
|---|---|
| `salon.json` | Atelier Noor, 14 Rue de Turenne, 75003 Paris. Owner Noor Haddad; stylists Léa and Marc; three chairs; Majirel colour line; FR jurisdiction. |
| `shade_map.json` | 16 Majirel-style shades with hex, undertone and level. The salon edits this table on Floor; code never hard-codes a hex. |
| `skus.json` | 42 SKUs: 14 shade tubes (backbar), 16 retail products, 12 services. Prices in EUR cents. Codes referenced by `recommend_plan` are listed as constants at the top of that module. |
| `clients.json` | 12 synthetic clients, two visits each, six weeks apart. `cl-01` (Amira Benali) visit 1 is the demo consultation. Scan payloads are complete: colour tones, all 14 skin readings, hair diagnostics, face attributes. |
| `doctavian_templates.json` | Template ids for the consent family (per treatment class + combined), aftercare per service, price list, client terms and the platform agreement. `tpl_fixture_*` ids are placeholders until Doctavian credentials arrive; the adapter interface does not change. |
| `invoices/` | Three supplier invoices (TVA 20 %); one scanned-looking; `inv-0003-bad-math.pdf` carries a deliberate arithmetic error the quarantine policy must catch. |
| `intake/` | Three handwritten intake scans; `intake-03-adversarial.png` hides an instruction-injection line. |
| `adversarial/` | Extra adversarial inputs used by the quarantine tests. |
| `clients/` | Client selfies referenced by `image_ref`. Demo-licensed images only; not committed. |

All people, addresses, emails and readings are synthetic.
