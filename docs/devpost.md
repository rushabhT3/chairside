# Devpost submission fields

Project page: https://api-cloud-ai-hackathon-2026.devpost.com/ (create the project, tick all seven sponsor challenges, paste the fields below, edit until 10:00 AM PDT / 10:30 PM IST on 3 Sep 2026).

## Project name
Chairside

## Elevator pitch (≤ 15 words)
One prompt opens a salon. One selfie runs the consultation, consents, prices, and remembers.

## Built with
Google ADK, MCP, Perfect Corp YouCam API, SerpApi, Xano, Nutrient DWS, Foxit PDF Services + eSign, Doctavian, name.com, React, TypeScript, Cloudflare Workers

## Try it out
- Storefront (salon domain): https://ateliernoor.com
- Floor (pro console): https://rushabht3.github.io/chairside/floor/
- Mirror (client PWA): https://rushabht3.github.io/chairside/mirror/
- Storefront (fixtures): https://rushabht3.github.io/chairside/storefront/
- Xano backend: https://xqbd-rqmo-jj2a.m2.xano.io (workspace `chairside`, API groups `chairside-*`)
- Render bridge (holds the YouCam key so Mirror can render your own scan): https://chairside-mirror-render.insidious-stop.workers.dev/health
- Repo: https://github.com/rushabhT3/chairside

## Video
Master 3:00 on YouTube (public). Sponsor cuts (60–90 s each) are linked from the README's "Judges: start here" section.

## Challenges (tick all seven)
Perfect Corp · SerpApi · Xano · Nutrient · Foxit · Doctavian · name.com

## About the project (paste)

**Inspiration.** A salon consultation decides whether a client returns, and every incumbent (Mindbody, Vagaro, Fresha, Zenoti) stores it as a notes field. Chairside makes the consultation the product: diagnosed, simulated on the client's own face in the salon's own shades, priced against today's market, consented, sold, rebooked, remembered.

**What it does.** Act 1: one prompt opens a salon. The Onboarding Agent registers a domain and DNS on name.com, generates the salon's consent family with Doctavian, gets the platform agreement signed by a human through Foxit eSign, parses the salon's paper price list and supplier invoices with Nutrient DWS into a catalog with per-field confidence, seeds market prices with SerpApi, maps the salon's shade line to YouCam inputs, and deploys a storefront on the new domain. Act 2: one selfie at the chair. The Consultation Agent runs four YouCam analyses over MCP, builds a plan from a deterministic table (never from the model), renders the plan in the salon's shades, identifies the bottle in the client's hand with Google Lens, prices it against Google Shopping, checks Google News for recalls, reads competitor reviews for staff only, selects the consent template by treatment class, extracts the handwritten intake with confidence, and hands the signature to a human through a gate the agent has no key for. One tap closes the sale: plan → order → rebooking, attributed to stylist and chair.

**How we built it.** Python 3.12 + Google ADK 2.8 for the two agents, with Foxit's open-source PDF MCP server and both YouCam MCP servers mounted as toolsets. Xano is the system of record, the auth, the nightly price engine, the signing gate (the only process holding eSign credentials), the static host, and an MCP server other agents can book through. Vite + React for Mirror (client PWA) and Floor (pro console). Every step is an event; the ledger is a SHA-256 hash chain verified in the browser. Fixtures mode replays recorded vendor responses so the whole flow runs on zero credits.

**Challenges.** Keeping the model out of anything that affects money, consent, or data: five pure functions decide the plan, the price policy, the consent template, the shade mapping, and the quarantine verdict, and the model only narrates. Drawing the signing boundary as a credential rather than a prompt, and filming the agent failing to cross it.

**What's next.** Payments, multi-location, and native Mirror.
