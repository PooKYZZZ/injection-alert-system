FROM node:20-alpine

WORKDIR /app

ARG AUTH_SECRET

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN AUTH_SECRET=${AUTH_SECRET:-docker-build-only-secret} npm run build

EXPOSE 3000

CMD ["sh", "-c", "npm start -- --hostname 0.0.0.0 --port ${PORT:-3000}"]
