# Reddit /r/MachineLearningEspanol (o equivalente) draft

> Subreddits posibles:
> - r/MachineLearningEspanol (chico pero activo)
> - r/datascienceenespanol
> - r/programacion
> - r/Argentina, r/chile, r/mexico (segun donde queres meter mas)
>
> Voz: misma editorial+understated pero en espanol natural rioplatense.
> No "lanzamos!!!" ni "checa esto!". Sin exclamaciones, sin emoji.

---

**Titulo:**
> [Proyecto] The Daily Abstract — newsletter diario de arXiv que podes responder por los PDFs

**Cuerpo:**

Construi una herramienta para investigadores que sufrimos viendo 200+
papers nuevos de arXiv todos los dias.

## Que hace

- Eleges tus categorias de arXiv (con keywords opcionales y un tope diario)
- A las 7am te llega un email con los papers nuevos que matchean
- **Respondes el email con los numeros ("1 3 5") y te llegan los PDFs
  adjuntos**, en ~30 segundos
- Titulos y abstracts traducidos al español (los originales a un click) —
  intencional, hay 500M hispanohablantes y casi ninguna herramienta de
  arXiv los considera
- Un click para gestionar suscripcion / darse de baja

## Por que se los muestro

El proyecto es open source y gratuito. Quiero feedback de gente que vive
en arXiv:

- ¿El flujo "responder por los PDFs" resuelve un problema real?
- ¿Que categorias te gustaria que tuviera presets curados?
- ¿Te servirian resumenes generados por LLM (Claude/GPT) como diferenciador?

## El stack

Todo en https://github.com/f3r21/arxiv-digest, licencia MIT.

- FastAPI + Jinja para la web
- Docker Compose con 6 servicios
- Corre en Oracle Cloud Free Tier (1 GB RAM, AMD E2.1.Micro) — el stack
  idle usa ~165 MB
- Brevo (SMTP gratis) para enviar, Mailsac (inbox gratis) para recibir
  replies
- HTTPS via Caddy + Let's Encrypt automatico
- Costo de hosting: $0/mes mientras Oracle mantenga el free tier

## Para suscribirse

https://arxivdaily.ignorelist.com — double opt-in (te llega un mail de
confirmacion antes de activarte), sin trackers, sin analytics, sin ads.

## Para auto-hostearlo

`docker compose up` con un `.env.prod` configurado. Documentado en
`DEPLOY.md` del repo.

---

Cualquier feedback, critica o sugerencia es bienvenida — especialmente de
investigadores de la region. Si conoces a alguien que podria interesarle,
compartilo.
