# FAIM Frontend Production Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (legacy-peer-deps for safety)
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy code (env files included so NEXTAUTH_SECRET is available at build time)
COPY . .

# Build — Next.js needs NEXTAUTH_SECRET during page data collection
# The .env file is already copied above; override only if passed as build-arg.
ARG NEXTAUTH_SECRET
ARG NEXTAUTH_URL=http://localhost:8010
ARG API_HOST=api:8000

# Only write to .env if ARG was supplied (leave file-based secret in place otherwise)
RUN if [ -n "$NEXTAUTH_SECRET" ]; then \
  printf "\nNEXTAUTH_SECRET=%s\nNEXTAUTH_URL=%s\n" "$NEXTAUTH_SECRET" "$NEXTAUTH_URL" >> .env; \
  fi

RUN npm run build

# Runner stage
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Next.js listens on PORT env var; defaults to 3000, we override to 8010
ENV PORT=8010

# Copy build artifacts
COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json



EXPOSE 8010

# Start Next.js serving.
CMD ["node_modules/.bin/next", "start", "-p", "8010"]
