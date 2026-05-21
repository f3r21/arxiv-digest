# Email audit — The Daily Abstract

Auditoria de los 3 emails contra `docs/BRAND_VOICE.md` y `docs/DESIGN_BRIEF.md`.
Prioridad: **compatibilidad first** (Gmail/Outlook/Apple Mail). Inline styles,
tables, cream light, no CSS moderno.

## Inventario

| Email | Template | Plain text? | Trigger |
|---|---|---|---|
| **Digest** | `digest/templates/digest.html` + `.txt` | ✓ | Cron diario + run_digest |
| **Confirm** | `subscriptions/templates/email_confirm.html` + `.txt` | ✓ | POST /subscribe |
| **Reply** (PDFs) | `listener/email_sender.py::send_reply` (string concat) | ❌ no HTML, **plain text crudo** | Polling Mailsac → reply parsing |

## Severidad por email

### Reply email (CRITICAL — el peor del set)
- ❌ Solo plain text. Después de un digest editorial cuidado, esto rompe la
  identidad por completo.
- ❌ Sin masthead "The Daily Abstract" — el usuario no asocia visualmente.
- ❌ Body es `"PDFs solicitados: [1, 2]\n\nAqui los adjuntos:\n  [ 1] Title..."`
  — telegráfico, sin contexto.
- ❌ Sin link de manage/unsubscribe — no compliance friction pero sí pierde
  coherencia con digest.
- ❌ Subject hereda del digest pero deberia decir algo afirmativo
  ("Your papers" o "Here are the PDFs you asked for").

**Fix:** rebrand completo con HTML editorial mantieniendo plain text alt.
Refactor a Jinja templates como los otros. Agregar manage/unsubscribe URLs
(requiere mover token signing a listener — paralelo a digest/manage_tokens.py).

### Digest (HIGH — funciona pero hay quick wins)

**Strengths:**
- Editorial layout solido (cream, Georgia, hairlines, Editor's Pick)
- Footer con manage/unsub OK
- Subject ya dice "The Daily Abstract No. X"

**Issues:**
1. **Acentos perdidos** — Spanish strings sin tildes: "numeros", "Tambien",
   "enviara", "Cancelar suscripcion". Fix a UTF-8 propio: "números", "También",
   "enviará", "Cancelar suscripción".
2. **Hidden `me-issue-wrap`** — el span `style="display:none"` poblado por JS
   nunca se llena en email (sin JS). Cleanup.
3. **Authors truncation** — `authors|join(', ')|truncate(80)` corta feo. Mejor
   pattern: "First Author, Second Author et al." cuando >3.
4. **No "View in browser"** — agregar link a `/preview` en footer para usuarios
   que prefieren web.
5. **Read time estimate** — "~5 min read" antes del Editor's Pick ayuda
   commitment.
6. **Date weekday** — "Wednesday, 21 May 2026" se siente más editorial que
   "21 May 2026".

### Confirm email (MEDIUM — funcional pero plano)

**Strengths:**
- Clean, single CTA, manual link fallback, anti-phishing footer

**Issues:**
1. **Sin "What you'll get" preview** — solo lista cats. Agregar:
   "Tomorrow at 7am you'll receive your first edition with new papers in:".
2. **Cats como `<li><code>`** — funciona pero los pills amber del confirm_ok
   serían más visualmente alineados con el resto del producto.
3. **CTA "Confirm subscription"** — adecuado. Variante "Confirm and start
   tomorrow" más vendedor pero presumido.
4. **Masthead minimo** — vs digest que tiene category_label + issue + date.
   Confirm puede agregar "Volumen I · Day 0".

## Priority queue (en orden de implementación)

1. **Reply email rebrand** (CRITICAL — gap mas grande) — HTML editorial coherente
2. **Acentos Spanish** en digest.html + digest.txt
3. **Authors et al. pattern** en digest
4. **View in browser** link en digest footer
5. **Confirm: pills + first-edition preview** copy
6. **Date format con weekday** (opcional, ver si encaja)

## Fuera de scope (Fase 3+)

- Dark mode @media query — usuarios con Apple Mail dark mode ven cream forced.
  Trade-off conciente (consistencia visual vs preferencia OS).
- Custom @font-face — Georgia funciona en todo, no vale la pena la pelea.
- Animated GIFs — Outlook desktop los rompe.
- Read receipts / tracking pixels — explícitamente NO (per privacy.md).
- Per-paper inline summary AI-generated — Fase 2 con LLM relevance scoring.
