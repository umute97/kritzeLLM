# syntax=docker/dockerfile:1

# --- Build: the static app into /app/dist ------------------------------------------------
FROM node:24.22.1-alpine3.24 AS build

WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
RUN npx vite build

# --- Runtime: nginx serves the app and hands /api to the api service ---------------------
FROM nginx:1.30.6-alpine3.24

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="kritzellm-web" \
      org.opencontainers.image.version="${APP_VERSION}"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1/healthz"]
