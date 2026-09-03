# Lighthouse: Mirror (mobile)

Run on 3 Sep 2026 against the production build served by `vite preview` (Lighthouse 12, headless Chrome, mobile form factor, default throttling).

| Category | Score |
|---|---:|
| Performance | 98 |
| Accessibility | 100 |
| Best practices | 100 |
| SEO | 100 |

Metrics: FCP 1.6 s · LCP 2.0 s · TBT 110 ms · CLS 0.001.

What moved the score: the Google Fonts stylesheet loads non-blocking with a `noscript` fallback, the Welcome shell is pre-rendered in `web/mirror/index.html` so the largest text paints before the bundle executes, and `public/robots.txt` plus meta descriptions cover the SEO audits.

Reproduce:

```bash
cd web && npm run build && npx vite preview --port 4173
npx -y lighthouse@12 http://localhost:4173/mirror/ --form-factor=mobile --chrome-flags="--headless=new" --output=json --output-path=./lh.json
```
