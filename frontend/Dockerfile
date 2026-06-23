FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build-only sentinel satisfies Auth.js secret presence checks at compile time
# without passing real runtime secrets into image build metadata.
RUN AUTH_SECRET=__BUILD_AUTH_SENTINEL_DO_NOT_USE__ NEXTAUTH_SECRET=__BUILD_AUTH_SENTINEL_DO_NOT_USE__ npm run build

EXPOSE 3000

CMD ["npm", "start"]
