FROM node:24-alpine AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

# Give each image build a distinct ID so Next.js can detect clients left on an
# older deployment. The value is compiled into the image, not supplied at runtime.
# Build-only sentinels satisfy Auth.js checks without embedding real secrets.
RUN NEXT_DEPLOYMENT_ID="$(node -p 'require("node:crypto").randomUUID()')" \
    AUTH_SECRET=__BUILD_AUTH_SENTINEL_DO_NOT_USE__ \
    NEXTAUTH_SECRET=__BUILD_AUTH_SENTINEL_DO_NOT_USE__ \
    npm run build

FROM node:24-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
