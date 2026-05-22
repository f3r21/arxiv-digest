# Outreach personal — primer round

> Objetivo: 1-3 personas reales suscriptas + feedback honesto antes de
> Phase F (HN/Reddit). Validar pull antes de invertir en launch grande.
>
> Voz: brand voice (editorial, understated) pero **personal y caliente**,
> no formal. Estás escribiendo a alguien que conocés, no a un newsletter.

---

## Quien priorizar (en orden)

1. **Compañeros de carrera/PhD** que sufren arXiv todos los días
   (los más probables a probarlo de verdad)
2. **Ex profesores o asesores** de tu área
3. **Gente de tu lab/grupo de investigación**
4. **Conocidos en Discord/Slack ML chicos** (eleuther, ML Collective,
   grupos de Latam)

Evitá por ahora: amigos no técnicos, gente que no esté en research/ML
(no son target persona y el feedback no escala).

---

## Templates

### 1) WhatsApp/Telegram corto (versión casual)

```
hey, hice algo que capaz te sirve

newsletter diario de papers de arXiv en las categorías que elijas,
en español, gratis. lo bueno: respondés el email con los números
de los papers que querés (ej "1 3 5") y te llegan los PDFs en
~30 segundos. sin trackear ni nada raro

https://arxivdaily.ignorelist.com

probalo, si lo usás contame qué romper
```

### 2) DM Twitter/X (un poco más profesional)

```
Hice un newsletter diario de arXiv con un feature que no encontré
en otros tools: respondés el email con los números de los papers
y te llegan los PDFs adjuntos. Free, open source, opcional Spanish.

Si te interesa el espacio o conocés a alguien que sufra arXiv:
https://arxivdaily.ignorelist.com

Feedback honesto >>> like.
```

### 3) Slack/Discord (post en canal de #general o #show-and-tell)

```
hice una herramienta para los que vivimos en arXiv:
The Daily Abstract — newsletter diario en tus categorías, en español
(opt-in inglés). Free, open source, hostable en una VM gratis.

Lo distintivo: el flow de "responder con números para recibir los PDFs
como attachments" — sin clickear 5 tabs.

Link: https://arxivdaily.ignorelist.com
Repo: github.com/f3r21/arxiv-digest

Si lo probás, me sirve feedback de:
- ¿el flow de reply-for-PDF se siente natural o raro?
- ¿qué categorías tendría que prebuildar como "presets"?
- ¿cómo se compara con arxiv-sanity-lite / Scholar Inbox para tu workflow?
```

### 4) Email cold (a un profesor o investigador)

```
Subject: Built a daily arXiv tool, would love your honest feedback

Hola [nombre],

Construí algo que me hubiese servido durante la cursada y pensé que
capaz te interesa: un newsletter diario de arXiv con dos features que
no encontré juntos en otras herramientas — respondés el email con los
números de los papers y te llegan los PDFs adjuntos en ~30 segundos,
y los títulos/abstracts vienen traducidos a español (opcional, los
originales a un click).

Es gratis, open source, hostable en una VM free tier de Oracle (~$0/mes
indefinido). Lo armé como proyecto de Cloud Computing pero quiero llevarlo
a producto real.

Link: https://arxivdaily.ignorelist.com
Código: github.com/f3r21/arxiv-digest

Si tenés 5 min y te interesa probarlo, tu feedback (especialmente
honesto/crítico) me sirve mucho. Si conocés a alguien de tu grupo o de
otras instituciones que podría darle uso, también.

Gracias,
[tu nombre]
```

---

## Qué medir / observar después de mandar

### Señales positivas (= pull real)
- Se suscriben en <24h (vs "lo voy a probar después" = murió)
- Confirman email (no quedan en pending)
- Responden al primer digest pidiendo PDFs (UX se entiende)
- Mandan feedback no solicitado (interés genuino)
- Comparten el link con otra persona

### Señales débiles (= producto no calza)
- Confirman pero no responden ningún digest = no estan abriendo el mail
  o el contenido no engancha
- "Lo voy a ver" sin nunca suscribirse = polite no
- Feedback tipo "está bueno" sin acción = polite no
- No share orgánico

### Métricas concretas a trackear
| Métrica | Cómo medirla | Threshold mínimo |
|---|---|---|
| % suscribe del link | manual (cuántos te decís dijeron sí) | >30% |
| % confirmación | DB `confirmed_at` vs `pending` | >70% |
| % open primer digest | Brevo dashboard / Gmail stats | >40% |
| % reply al primer digest | logs listener | >20% |
| Tiempo a primera reply | listener log timestamp | <72h |

---

## Anti-patterns a evitar

- ❌ Forwarding o BCCing en grupos grandes — sintiéndose spam
- ❌ Insistir si no contestaron en 1 semana — quedó claro
- ❌ Hablar de "1000 usuarios", "monetización", "Series A" — todavía
  no aplica
- ❌ Pedir Producto Hunt votes / GitHub stars en el primer touch
- ❌ Pretender que es más maduro de lo que es (1 subscriber, 1 día live)

---

## Acción concreta para esta noche

Identificá ahora mismo **3 personas específicas** y mandales el WhatsApp
template. Anotá quién y cuándo, y revisá en 48h:

| Persona | Canal | Enviado | Respondió | Suscrito | Confirmó | Primer reply |
|---|---|---|---|---|---|---|
| _____ | _____ | _____ | _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ | _____ | _____ | _____ |
