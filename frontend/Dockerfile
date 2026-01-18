# FAIM Frontend Production Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (legacy-peer-deps for safety)
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy code and build
COPY . .
RUN npm run build

# Runner stage
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Copy build artifacts
COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

# Start Next.js (standalone mode)
CMD ["node", ".next/standalone/server.js"]
