# Multi-stage build: Vite SPA → Caddy static server with backend reverse proxy.
# Build context must be the repo root so the Caddyfile is reachable.

FROM node:20-alpine AS builder
WORKDIR /app
COPY apps/frontend/package.json apps/frontend/package-lock.json* ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /app/dist /var/www/dispatch
COPY caddy/Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
