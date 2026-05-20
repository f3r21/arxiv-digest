# Deploy a Oracle Cloud Free Tier

Guía paso a paso para poner arxiv-digest en producción **gratis**: VM AMD
E2.1.Micro (1 GB RAM) + subdominio gratis con DNS completo (FreeDNS) +
Resend con dominio verificado (DKIM/SPF/DMARC) + imágenes pre-built en
Docker Hub.

**Por qué E2.1.Micro y no A1.Flex (4 OCPU / 24 GB):** A1.Flex está saturado
en la mayoría de regiones (`Out of capacity`) y multi-region requiere
upgrade a PAYG. E2.1.Micro siempre tiene capacidad. Medido localmente el
stack idle = 155 MB de RAM, cabe holgado en 1 GB.

Tiempo estimado: **60-90 min** la primera vez, mayormente esperas (verificación
de dominio, propagación DNS).

## Pre-requisitos

Cuentas (las cuatro gratis):

1. **Oracle Cloud** — `cloud.oracle.com`. Pide tarjeta de crédito para
   verificar identidad (no te cobra si te quedás en Always Free).
2. **Docker Hub** — `hub.docker.com`. Repos públicos ilimitados gratis.
3. **FreeDNS** — `freedns.afraid.org`. Solo email.
4. **Resend** — `resend.com`. Plan gratis: 100 emails/día, 3000/mes.

Y en tu laptop:
- Un par de claves SSH (`ssh-keygen -t ed25519` si no tenés).
- Docker Desktop (para hacer el build local de las imágenes).
- `git`.

---

## 1. Crear VM en Oracle Cloud (~15 min)

1. Login → home region (Santiago / Bogotá / cualquiera disponible al firmar).
2. Hamburguesa → **Compute → Instances → Create Instance**.
3. Settings:
   - **Name**: `arxiv-digest`
   - **Image**: `Canonical Ubuntu 22.04` (default)
   - **Shape**: clic en *Change Shape* → tab **AMD** → `VM.Standard.E2.1.Micro`
     (Always Free, 1/8 OCPU, 1 GB RAM). Sin sliders (shape fija). Capacidad
     siempre disponible — sin `Out of capacity`.
   - **Networking**: dejá el VCN/subnet default. Asegurate que
     "Automatically assign public IPv4 address" esté tildado. Si el toggle
     no responde, crear VM sin IP pública y asignarla después desde
     Instance details → Attached VNICs → IPv4 Addresses → Assign Public IP.
   - **SSH keys**: pegá tu `~/.ssh/id_ed25519.pub` (o la que uses).
   - **Boot volume**: default (47 GB) es suficiente.
4. **Create**. Cuando esté `Running`, anotá la **Public IP** (la vas a usar
   todo el resto del doc — llamémosla `<IP>`).
5. Abrir puertos 80 y 443:
   - Instance details → **Subnet** → **Default Security List** → **Add Ingress Rules**.
   - Source CIDR `0.0.0.0/0`, IP Protocol `TCP`, Destination Port Range `80,443`.

---

## 2. Conectar y preparar la VM (~10 min)

```bash
ssh ubuntu@<IP>
```

Una vez dentro de la VM:

```bash
# Update OS
sudo apt-get update && sudo apt-get upgrade -y

# Instalar Docker (script oficial)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# IMPORTANTE: Oracle Ubuntu trae iptables bloqueando todo por default.
# Abrir 80 y 443 dentro de la VM (la rule de Security List no es suficiente).
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
# (si netfilter-persistent no existe: sudo apt-get install -y iptables-persistent)

# Salí y volvé a entrar para que el group docker tome efecto
exit
ssh ubuntu@<IP>

# Verificar
docker version
docker compose version
```

---

## 2.5. Build y push de imágenes a Docker Hub (~5 min, en TU LAPTOP)

La VM E2.1.Micro tiene CPU muy limitada (1/8 OCPU) — buildear las imágenes
Python ahí toma 10-15 min y rosa el límite de RAM. Mucho mejor build local
y push a Docker Hub, la VM solo hace pull (1-3 min).

**En tu laptop** (no en la VM):

```bash
# Una sola vez: login en Docker Hub
docker login
# Username: tu username de hub.docker.com
# Password: usá un Personal Access Token, no tu password de la cuenta:
#   hub.docker.com → Account Settings → Security → New Access Token
#   permisos: Read, Write, Delete

# Cada vez que cambies código:
cd ~/path/to/arxiv-digest
DOCKERHUB_USER=tu-username ./tools/build_and_push.sh
```

El script construye las 4 imágenes con `--platform linux/amd64` (importa si
tu laptop es Mac M1/M2/M3, la VM es AMD) y las pushea a:

- `hub.docker.com/r/tu-username/arxiv-digest-subscriptions`
- `hub.docker.com/r/tu-username/arxiv-digest-digest`
- `hub.docker.com/r/tu-username/arxiv-digest-listener`
- `hub.docker.com/r/tu-username/arxiv-digest-translator`

Verificá en `hub.docker.com` que aparezcan los 4 repos públicos.

---

## 3. Registrar subdominio en FreeDNS (~5 min)

1. Login en `freedns.afraid.org`.
2. **Subdomains** (sidebar) → **Add a subdomain**.
3. Settings:
   - **Type**: `A`
   - **Subdomain**: lo que quieras (ej. `arxivdigest`)
   - **Domain**: cualquiera de la lista (`mooo.com`, `chickenkiller.com`, etc.
     son populares y estables).
   - **Destination**: la `<IP>` de tu VM.
   - **TTL**: 1800 (default).
4. **Save!** → quedaste con `arxivdigest.mooo.com` (por ejemplo).

Verificá la propagación:

```bash
dig +short arxivdigest.mooo.com
# debe devolver tu IP
```

Puede tardar de 1 a 10 min.

---

## 4. Verificar dominio en Resend (~10 min + esperas)

1. Login en `resend.com` → **Domains** → **Add Domain**.
2. Domain: poné tu subdominio entero (ej. `arxivdigest.mooo.com`). No el
   apex — Resend permite subdominios.
3. Resend te muestra **4 registros DNS** que tenés que crear:
   - 1 `TXT` (SPF): valor tipo `v=spf1 include:_spf.resend.com ~all`
   - 1 `TXT` o `CNAME` (DKIM): valor largo tipo `p=MII...`
   - 1 `MX` (return-path): tipo `feedback-smtp.us-east-1.amazonses.com` prio 10
   - 1 `TXT` (DMARC, opcional pero recomendado):
     `v=DMARC1; p=none; rua=mailto:tu@correo.com`
4. **Volvé a FreeDNS** → **Subdomains** → **Add a subdomain** por CADA uno:
   - Para TXT: type=`TXT`, subdomain=lo que diga Resend (ej. `resend._domainkey`
     para DKIM, `@` para SPF), destination=el valor.
   - Para CNAME: type=`CNAME`, subdomain= el que diga Resend, destination=el
     target.
   - Para MX: type=`MX`, subdomain=`send`, destination=el host. **Prefiero**:
     FreeDNS soporta MX en el plan gratis.
5. Volvé a Resend → **Verify Domain**. Puede tardar 5-60 min.

   ```bash
   # mientras esperás, verificá que los TXT se propagaron:
   dig +short TXT resend._domainkey.arxivdigest.mooo.com
   dig +short TXT arxivdigest.mooo.com
   ```

6. Cuando Resend dice **Verified**, anda a **API Keys** → **Create API Key** →
   permisos `Sending access`. Guardá la key — empieza con `re_`.

---

## 5. (Opcional) Inbox para replies con Mailsac

Si querés que los suscriptores puedan responder con números y recibir PDFs:

1. `mailsac.com` → signup → **Inboxes** → reservar uno (ej.
   `arxiv-replies@mailsac.com`).
2. **API & Webhooks** → crear API key.

Si NO necesitás reply→PDFs (los suscriptores reciben el digest con links
directos a arXiv y ya), saltate Mailsac. En `.env.prod` poné
`INBOX_BACKEND=mailsac` igual pero con la key dummy, o cambialo a `mailhog`
local y comentá el listener en el compose.

---

## 6. Clonar repo + configurar `.env.prod` (~5 min)

```bash
# en la VM
cd ~
git clone https://github.com/<tu-usuario>/arxiv-digest.git
cd arxiv-digest

cp .env.prod.example .env.prod
nano .env.prod
```

Rellenar mínimo:

```env
DOCKERHUB_USER=tu-username        # el mismo que usaste en build_and_push.sh

SUBSCRIPTIONS_DOMAIN=arxivdigest.mooo.com
PUBLIC_BASE_URL=https://arxivdigest.mooo.com
ADMIN_EMAIL=tu@correo.com
SUBSCRIPTIONS_SECRET=<openssl rand -hex 32>

SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASS=re_xxxxxxxx  # la key de Resend
SMTP_USE_TLS=1
FROM_ADDR=digest@arxivdigest.mooo.com
REPLY_TO=arxiv-replies@mailsac.com
RECIPIENT=tu@correo.com  # te auto-seedea como subscriber

INBOX_BACKEND=mailsac
MAILSAC_API_KEY=k_xxxxxxxx
MAILSAC_INBOX=arxiv-replies@mailsac.com
SELF_ADDR=digest@arxivdigest.mooo.com
POLL_INTERVAL_S=600

SEED_SUBSCRIBER_CATEGORIES=cs.DC,cs.AI
EXPOSE_ADMIN=0
```

Generá el secret en la VM:

```bash
openssl rand -hex 32
# pegá el output como SUBSCRIPTIONS_SECRET
```

---

## 7. Deploy! (~3 min)

```bash
./tools/deploy.sh
```

El script valida que `.env.prod` no tenga placeholders, hace
`docker compose pull` (descarga las 4 imágenes desde Docker Hub), luego
`up -d`, espera healthchecks y muestra status + URLs. **Sin build en la VM**
— por eso es rápido (~1-3 min vs 10-15 min de build directo).

Si todo va bien:

```bash
curl https://arxivdigest.mooo.com/health
# {"status":"ok"}

# Verificar que el stack cabe en RAM
docker stats --no-stream
# La suma de MEM USAGE debe ser <500 MB
free -h
# available debe ser >300 MB
```

La primera request a HTTPS hace que Caddy emita el certificado de Let's
Encrypt (puede tardar 30 s).

**Para actualizar código después:**
```bash
# en tu laptop
./tools/build_and_push.sh        # rebuilds + pushes
# en la VM
./tools/deploy.sh                # pull + up (Docker detecta cambios y reinicia)
```

---

## 8. Verificar end-to-end

1. **Form**: abrir `https://arxivdigest.mooo.com/` en el navegador. Suscribir
   tu propio email.
2. **Confirmación**: revisar inbox (Gmail). Si el email no llega:
   - Revisar spam.
   - `docker compose -f docker-compose.prod.yml --env-file .env.prod logs subscriptions`
     — buscar "RESULT: email enviado".
   - Si Resend dice rechazado, revisar verificación de dominio.
3. **Confirmar**: click en el link → ver "Listo".
4. **Disparar digest**:

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod exec digest \
     python -c "from main import run_digest; run_digest()"
   ```

   Si arXiv te bloquea (`fetched 0 papers`), esperá unas horas o probá con
   menos categorías. Para la demo, dispará con horas de antelación.

5. **Reply→PDFs**: responder el digest desde el Gmail con "1 3 5". El
   listener (poll cada 10 min en prod) levanta el reply de Mailsac y te
   devuelve los PDFs adjuntos.

---

## 9. Preparar la demo de clase

```bash
# en tu laptop
brew install qrencode    # macOS
qrencode -o digest-qr.png "https://arxivdigest.mooo.com/"
```

Slide simple:
- Título: "arxiv-digest - suscribite"
- QR centrado, grande
- URL como texto debajo (por si el QR no scaneo)
- "Elegí tus categorías arXiv. Recibís un digest diario, podés responder con números y te llegan los PDFs."

Plan B: si arXiv blockea durante la demo, dispará un `run_digest` con papers
mockeados igual que hiciste en testing (override de `fetch_papers`).

---

## Troubleshooting

**Caddy no emite cert.**
```bash
docker compose -f docker-compose.prod.yml logs caddy | grep -i acme
```
Causas comunes: DNS no propagado (`dig` tu dominio), puertos 80/443 cerrados
en Oracle Security List o iptables, dominio con typo en `.env.prod`.

**Resend rechaza emails.**
- Verificar que el dominio está `Verified` en Resend dashboard.
- Verificar que `FROM_ADDR=digest@TU-DOMINIO` (no el sandbox `onboarding@resend.dev`).
- Plan free: 100/día — chequear cuota.

**Mailsac no recibe replies.**
- Verificar que `REPLY_TO=tu-inbox@mailsac.com` matchea el inbox creado.
- Confirmar API key activa.

**Out of memory** (posible en E2.1.Micro de 1 GB; el stack idle usa ~155 MB).
```bash
docker stats
free -h
# Si algún container murió con exit 137 (OOM kill):
docker compose -f docker-compose.prod.yml --env-file .env.prod logs <svc> | tail
# Subir el limit en docker-compose.prod.yml para ese servicio (+50 MB)
# y rebuild/repush en local, luego ./tools/deploy.sh
```

Como fallback, podés crear un swap file de 1 GB en la VM:
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

**Update del código** (después de cambiar algo en tu laptop).
```bash
# en tu laptop
./tools/build_and_push.sh        # rebuild + push de las 4 imágenes
# en la VM (SSH)
cd ~/arxiv-digest
./tools/deploy.sh --git-pull     # git pull (para refrescar compose/Caddyfile) + pull imágenes + up
```

**Build de imágenes en Mac M1/M2/M3.**
El script `build_and_push.sh` ya pasa `--platform linux/amd64`. Para verificar
que la imagen subida es AMD64 (la VM la rechazaría si subiste ARM):
```bash
docker manifest inspect tu-username/arxiv-digest-subscriptions:latest | grep architecture
# debe decir "amd64"
```

**Logs útiles.**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f digest
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f subscriptions
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f caddy
```

---

## Costos esperados

| Componente | Plan | Costo |
|---|---|---|
| Oracle Cloud VM (AMD E2.1.Micro) | Always Free | $0 |
| Docker Hub | Free (repos públicos ilimitados) | $0 |
| FreeDNS subdomain | Free tier | $0 |
| Resend SMTP | Free (100 emails/día) | $0 |
| Mailsac inbox | Free (1500 calls/mes) | $0 |
| **Total** | | **$0/mes** |

Si superás los 100 emails/día de Resend (~150 suscriptores que reciben todos
los días), Resend cobra **$20/mes por 50k emails**. Mucho margen.
