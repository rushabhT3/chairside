# Video script 2 — speak this

Rule: short sentences. Pause at every period. If you stumble, finish the sentence and keep going. Cuts are easy, restarts are expensive.

Target 3:00. Hard ceiling 3:00 for the main challenge, and Perfect Corp wants 1 to 3 minutes, so this length satisfies both.

**Before recording**

- Browser window at 1280 wide, no bookmarks bar, no extensions visible.
- Tab 1: `https://rushabht3.github.io/chairside/mirror/` freshly loaded, camera permission already granted.
- Tab 2: `https://rushabht3.github.io/chairside/floor/`
- Terminal open in `C:\rough\Assessments\chairside\agent`, font large, cleared.
- Run `uv run chairside_agent reset` once before recording so the ledger is empty.
- Sit at arm's length, plain wall behind you, face lit from the front.

---

## 1 · THE PROBLEM — 0:00 to 0:30

**Screen: Mirror welcome screen, "Atelier Noor".**

> This is Chairside.
>
> A salon consultation decides whether a client comes back. Every booking system on the market stores it as a notes field.
>
> So the colour that worked last spring is a memory. The allergy is on paper in a drawer. And the consent that protects the salon is a signature nobody can produce two years later.
>
> Chairside makes the consultation itself the product.

## 2 · ONE PROMPT OPENS A SALON — 0:30 to 1:05

**Screen: terminal. Run the open command. Let the event lines scroll.**

```
uv run chairside_agent open "Open Chairside for Atelier Noor, 14 Rue de Turenne, 75003 Paris. Hair, skin, brows. Three chairs. Owner: Noor Haddad, noor@example.com."
```

> One prompt opens a salon.
>
> The agent registers the domain and the DNS records on name dot com. It generates the consent family with Doctavian. It sends the platform agreement to the owner through Foxit eSign.
>
> Then it reads the salon's paper price list and their supplier invoices with Nutrient. Forty two rows, a hundred and sixty eight fields, each with a page, a box and a confidence score.

**Point at the `onboarding.done` line.**

> Forty two products, one flagged for human review, a storefront deployed. From one sentence.

## 3 · ONE SELFIE RUNS THE CONSULTATION — 1:05 to 1:50

**Screen: Mirror. Tap Start your scan, then Scan. Let the analysis steps tick through to the card.**

> Act two happens at the chair. One selfie.
>
> YouCam reads skin, hair and face. Fourteen skin concerns, hair type, face shape, undertone.
>
> And then the plan. This is the part that matters. The plan does not come from a language model. It comes from a table. Five pure functions own the plan, the price, the consent template, the shade mapping and the quarantine verdict. The model only narrates what the code decided.

**Screen: tap Simulate. Pick a shade chip. Wait for the render, then drag the slider.**

> Those are the salon's own shades, on my face, rendered by Perfect Corp while you watched.
>
> The key for that never touches the browser. A worker holds it, takes the scan, and returns the render.

## 4 · THE AGENT CANNOT SIGN — 1:50 to 2:30

**Screen: terminal. Run the red team command.**

```
uv run chairside_agent redteam esign
```

> Now the part I actually want judged.
>
> This agent can generate a consent form. It can price a treatment. It can book a chair. It cannot sign anything, and not because I told it not to.
>
> This command makes the agent attempt the eSign call with every credential it holds.

**Let the 401 land. Point at it.**

> Four oh one. The signing credential lives only in Xano. The agent process never had it.
>
> Xano refuses six different ways: the agent's own service token, a client's token, a document still in draft, an onboarding whose documents are unreviewed, a consent that is not ready, and no token at all. All six are run against the live backend and written down.

**Screen: Floor ledger. Scroll to the `redteam.esign_denied` row.**

> And the refusal is in the ledger, in a SHA-256 hash chain the browser re-verifies. Change one row and the page catches it.

## 5 · WHAT IS REAL — 2:30 to 3:00

**Screen: terminal, run replay. Then back to Mirror.**

```
uv run chairside_agent replay cons-0001
```

> Every step of both agents is an event. The console, the ledger and this replay are all projections of that one stream. Fifty eight events fold back to the stored result.
>
> Six of the seven vendor integrations run on responses recorded from the live APIs today, and the repository says exactly which are which.
>
> Running those live found four bugs no fixture would have caught. Google Maps rejects a plain coordinate pair. YouCam's hair diagnostics need three camera angles. Foxit's own MCP server ships an entry point that cannot start.
>
> Chairside. The model narrates. The code decides. And the agent cannot sign.

---

## If a shot fails while recording

- **A render says come closer or move back.** Say "framing matters, the mirror tells you what to fix", change distance, scan again. It is a good moment, not a bad one.
- **The skin tab times out.** Skip it. Use the hair tab, which is the fastest and the most visual.
- **The camera does not open.** Use the file picker on the scan screen and choose a photo of yourself. Same pipeline.
- **A terminal command is slow.** Keep talking. Do not stop and wait in silence.
