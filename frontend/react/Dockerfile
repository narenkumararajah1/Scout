# Builds the SPA and serves it from nginx, which also proxies the API so
# that browser and API share one origin - see deploy/nginx.conf.
#
# **Build from the repository root**, not from this directory, because
# the image needs deploy/nginx.conf as well as this app:
#
#     docker build -f frontend/react/Dockerfile -t scout-frontend .
#
# docker-compose.yml already sets the context this way.

# ---------- build ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Copied first so a dependency install is only redone when the manifests
# change, not on every source edit.
COPY frontend/react/package.json frontend/react/package-lock.json* ./
# `npm ci` rather than `install`: it honours the lockfile exactly, which
# is the difference between a reproducible image and a surprise.
RUN npm ci

COPY frontend/react/ ./

# Baked in at build time, not read at runtime - Vite inlines VITE_* into
# the bundle, so changing this needs a rebuild, not a restart. It must
# match the backend's REQUIRE_AUTHENTICATION: with the two disagreeing,
# the app either shows a login screen guarding nothing, or skips the
# redirect and renders a page full of 401s.
ARG VITE_REQUIRE_AUTH=true
ENV VITE_REQUIRE_AUTH=$VITE_REQUIRE_AUTH

RUN npm run build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# 127.0.0.1, not localhost: nginx.conf says `listen 80`, which binds
# IPv4 only, while busybox wget resolves localhost to ::1 first and gets
# "connection refused". The site serves perfectly from outside - only
# the check fails - so the container reports unhealthy while working,
# which is the kind of false alarm that makes people ignore health
# status. Observed on the first containerised run.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --spider http://127.0.0.1/index.html || exit 1
