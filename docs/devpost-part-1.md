# Devpost part 1 — paste these fields

Everything below is ready to paste. Fields appear in the order Devpost asks for them.

---

## General info

**Project name**

```
Chairside
```

**Elevator pitch** (200 characters)

```
One prompt opens a salon. One selfie runs the consultation: diagnosed, simulated on the client's own face, priced against today's market, consented, sold, remembered.
```

---

## Project details

### About the project

Paste everything between the rules into the "About the project" box. It is Markdown, which Devpost renders.

---

## Inspiration

A salon consultation decides whether a client comes back, and every incumbent stores it as a notes field. Mindbody, Vagaro, Fresha and Zenoti all treat the most important five minutes in the chair as free text somebody types afterwards, if they remember.

So the colour that worked last spring is a memory. The allergy is on a paper form in a drawer. The price the client saw online is a guess. And the consent that protects the salon is a signature nobody can produce two years later.

We wanted to make the consultation itself the product: diagnosed, simulated on the client's own face, priced against the market that morning, consented, sold, rebooked and remembered.

## What it does

Chairside is two acts.

**Act one opens a salon from one prompt.** The onboarding agent registers a domain and DNS on name.com, generates the salon's consent family with Doctavian, gets the platform agreement signed by a human through Foxit eSign, parses the salon's paper price list and supplier invoices with Nutrient into a catalogue with per-field confidence, seeds market prices with SerpApi, maps the salon's own shade line to YouCam inputs, and deploys a storefront on the new domain.

**Act two runs a consultation from one selfie.** The client scans at the chair. YouCam analyses skin, hair and face. A deterministic table, not a model, builds the plan. The chosen shades are rendered on the client's own face. Google Lens identifies the bottle in their hand, Google Shopping prices it, Google News checks it for recalls. The consent template is selected by treatment class, the handwritten intake is extracted with confidence scores, and the signature is handed to a human through a gate the agent has no key for. One tap turns the plan into an order, a booking and an attribution to stylist and chair.

Three surfaces: Mirror is the client's phone, Floor is the stylist's console, Storefront is the salon's public site.

## How we built it

Python 3.12 and Google ADK for the two agents, with Foxit's open-source PDF MCP server and both YouCam MCP servers mounted as toolsets. Vite, React and TypeScript for the three web apps.

Xano is the system of record, the auth, the nightly price engine, the signing gate and an MCP server other agents can book through. It is also the only process that holds the eSign credential. The agent cannot sign, and we can prove it: `chairside_agent redteam esign` makes the agent attempt the call with the credential it does have, receives 401, and writes `redteam.esign_denied` into the ledger.

Every step of both agents writes an event. Floor, the ledger and `chairside_agent replay <id>` are all projections of that stream, and the audit trail is a SHA-256 hash chain the browser re-verifies.

The rule we held to throughout: the model narrates, the code decides. Five pure functions own the plan, the price policy, the consent template, the shade mapping and the quarantine verdict. Nothing a model returns can move money, change consent, or release data.

Rendering the client's own face needed care. A browser cannot hold a vendor API key, so a small Cloudflare Worker holds it, takes the scan, runs the YouCam task and returns the render. The key never reaches the browser and never enters the repository.

## Challenges we ran into

**Drawing the signing boundary as a credential, not a prompt.** It is easy to tell a model not to sign things. It is worth something to make signing impossible. Moving the eSign credential into Xano meant the agent physically cannot cross the line, and filming it fail is more convincing than any system prompt.

**Live APIs disagree with their documentation.** Google Maps rejects a bare latitude and longitude pair and wants an `@lat,lng,zoom` string, and refuses a page size on the first page of reviews. YouCam's hair type and frizziness tasks need three camera angles, not one. Foxit's own MCP server ships a console script pointing at a module its wheel does not contain, and wraps every tool result in a JSON string under another key. Every one of those was invisible until we ran a real call.

**Handwriting is genuinely hard.** Live extraction read a client's name as "Awura Benalv". That is not a bug to hide, it is the reason the extraction carries per-field confidence and why a human reviews the intake.

**The demo lied and we caught it.** Our own scan screen captured a photo, hashed it, and then showed a stock model's face. It looked like a product until you used it. Fixing that late, with the worker, mattered more than any feature we could have added instead.

## Accomplishments that we're proud of

Six of the seven sponsor integrations replay responses recorded against the live APIs, not invented fixtures, and the repository says exactly which are which and why.

The signing gate is proven live against six separate refusal reasons, including the agent's own service token being rejected outright.

The audit chain is verified in the browser, so a judge can tamper with a row and watch the page catch it.

And the simulate screen renders on the person actually standing in front of it.

## What we learned

Recording against real vendors changes the design. Four integration bugs only surfaced when a real API answered, and every one of them would have shipped behind a hand-written fixture that agreed with our assumptions.

Confidence scores are worth more than accuracy. The extraction that misreads a name at 0.4 confidence is more useful than one that misreads it at 0.95.

And a demo that fakes its central moment is worse than a demo that admits its limits.

## What's next for Chairside

**Finish the live scan path.** The client's own photo now drives the simulate screen through the render worker, but the readings card still replays recorded analyses. The same bridge should carry colour tones, skin analysis and face attributes, so every number on the card comes from the face in front of the mirror.

**Make the skin simulation dependable.** It is the fussiest of the three renders about framing and the slowest to return, and it still times out on some scans. It needs an asynchronous job the client polls, plus on-screen framing guidance before the shutter rather than an error after it.

**Harden the capture itself.** Camera start, focus and framing vary a lot across phones, and the one-face check falls back to a skin-tone heuristic where the browser has no face detector. This deserves a proper on-device detector and a live framing guide.

**Rebuild the interface.** The three apps are honest but plain. The mirror in particular is a device a client stares at for ten minutes, and it should feel like the best-looking thing in the salon.

Then payments, multi-location, and a native Mirror.

---

### Built with

Paste as tags, up to 25.

```
python, typescript, react, vite, google-adk, mcp, xano, xanoscript, perfect-corp-youcam, serpapi, nutrient-dws, foxit-pdf-services, foxit-esign, doctavian, name.com, cloudflare-workers, github-actions, pydantic, httpx, sha-256, event-sourcing, vitest, pytest, google-gemini
```

### Try it out links

```
https://rushabht3.github.io/chairside/mirror/
https://rushabht3.github.io/chairside/floor/
https://rushabht3.github.io/chairside/storefront/
https://github.com/rushabhT3/chairside
https://chairside-mirror-render.insidious-stop.workers.dev/health
```

### Project thumbnail

Upload `docs/media/project-thumbnail.png`. It is 1200 by 800, the 3:2 ratio Devpost asks for, under 5 MB.

### Image gallery

Upload `docs/media/architecture.png` first, so it sits at the top of the gallery. Then add screenshots as time allows:

1. `docs/media/architecture.png` — the architecture diagram, explained below.
2. Mirror simulate screen with a face rendered in a salon shade.
3. Floor ledger showing the hash chain with the `redteam.esign_denied` row.
4. Terminal showing `redteam esign` returning HTTP 401.
5. Floor chairs view.

### What the architecture diagram shows

Paste this as the caption on the diagram, or drop it into the story under "How we built it".

The diagram reads left to right, and the whole point is the third column.

**Surfaces.** Mirror is the client's phone: it opens the camera, checks exactly one face is in frame, resizes, hashes the bytes and collects consent. Floor is the stylist's console and re-verifies the audit chain in the browser. Storefront is the salon's public site. The render worker sits beside them because a browser cannot hold a vendor API key, so a Cloudflare Worker holds it, takes the scan and returns the render.

**Agents.** Two of them, onboarding and consultation. Between them sit five pure functions that own the plan, the price policy, the consent template, the shade mapping and the quarantine verdict. Nothing a language model returns reaches those functions. The model narrates what they decided. Every step either agent takes is written as an event, and the console, the ledger and `replay` are three projections of that one stream.

**Xano.** The system of record, the auth, the nightly price engine and an MCP server other agents can book through. Two boxes are outlined in red. The commit gate refuses to send a signing envelope six different ways: an agent service token, a client token, a document still in draft, an onboarding whose documents are unreviewed, a consent that is not ready, and no token at all. Below it, the eSign credential exists only as a Xano workspace variable. The arrow shows the agent trying and being told 401 or 403. That refusal is the product, not a limitation of it.

**Vendors.** Six of the seven integrations replay responses recorded against the live APIs on 3 September 2026, marked in green. Foxit eSign is deliberately unreachable from the agent. Doctavian issues credentials by email and stayed on fixtures. Every adapter has both a live path and a fixtures path, so the entire flow runs on zero credits, and the audit chain means a judge can tamper with any row and watch the page catch it.

### YouTube title

```
Chairside: an AI agent that runs a salon consultation and cannot sign anything
```

### YouTube description

```
Chairside turns the salon consultation into the product. One prompt opens a salon. One selfie runs the consultation: skin and hair diagnosed, the salon's own shades rendered on the client's face, the plan priced against today's market, consent signed by a human, and the whole thing replayable from an event log.

The rule throughout: the model narrates, the code decides. Five pure functions own the plan, the price policy, the consent template, the shade mapping and the quarantine verdict. Nothing a language model returns can move money or change consent.

And the agent cannot sign. Not because it was told not to. The eSign credential lives only inside Xano, so when the agent tries, it gets a 401 and the refusal is written into the audit chain. That moment is in the video.

Built for the DevNetwork [API + Cloud + AI] Hackathon 2026.

Try it
Mirror, the client app: https://rushabht3.github.io/chairside/mirror/
Floor, the stylist console: https://rushabht3.github.io/chairside/floor/
Storefront: https://rushabht3.github.io/chairside/storefront/
Code: https://github.com/rushabhT3/chairside

Built with
Perfect Corp YouCam, Xano, SerpApi, Nutrient DWS, Foxit PDF Services and eSign, name.com, Doctavian, Google ADK, MCP, Cloudflare Workers, React, TypeScript, Python.

Six of the seven vendor integrations replay responses recorded against the live APIs, and the repository states exactly which are real and which are fixtures.

Chapters
0:00 The problem
0:30 One prompt opens a salon
1:05 One selfie runs the consultation
1:50 The agent cannot sign
2:30 What is real
```

Visibility Public, not Unlisted. Keep the first chapter at 0:00 or YouTube ignores all of them.

### Video demo link

The YouTube URL, public, not unlisted. Use `docs/media/yt-thumbnail.png` as the video's custom thumbnail, it is 1280 by 720.

---

## Additional info, for judges

### Sponsor / special prizes

Tick all seven:

- Perfect Corp: Building the Next Generation of AI-Driven Consumer Experiences
- Foxit Software: Your Agent Shouldn't Sign That
- Doctavian: Generate It Right. Sign It Tight.
- name.com: Domain API Challenge
- Nutrient: Turn Documents Into Something People Actually Trust
- SerpApi: Best AI Use Case
- Xano: Rebuild a SaaS Tool You Hate

### Downloadable backup of the demo video

Upload the original MP4 to Google Drive, set sharing to "Anyone with the link can view", and paste that link. Answer text:

```
Original MP4: <paste the Google Drive share link here>
Sharing is set to anyone with the link, no sign-in required.
```

### Upload a file

Optional. Skip it unless you have time. If you do upload something, the most useful file is `docs/xano-live-gate.md`, which is the commit gate matrix run against the live backend.

### Xano challenge, extra questions

The Xano challenge asks four questions in its own brief. Short answers:

**What software did you replace?** The consultation and client-record half of Mindbody, Vagaro, Fresha and Zenoti.

**Why did you choose Xano?** It holds the parts that must not live in the agent: the data, the auth, the price engine and the eSign credential. The signing gate is a Xano function, so the boundary is enforced by the backend rather than by a prompt.

**Which AI tools did you use?** Claude Code.

**How long did it take?** One day.

**What would have taken significantly longer without AI and Xano?** Writing and wiring seven vendor integrations with contract tests, and building the backend, auth and gate logic behind them.
