# FAIM Frontend Production Dockerfile
FROM node:22-alpine AS builder

WORKDIR /app

# Install system dependencies (libc6-compat needed for Next.js binary compatibility on Alpine)
RUN apk add --no-cache libc6-compat
ENV NEXT_TELEMETRY_DISABLED=1

# Install dependencies (legacy-peer-deps for safety)
COPY package*.json ./
RUN npm config set fetch-retry-maxtimeout 120000 && \
  npm config set fetch-retries 5 && \
  npm install --legacy-peer-deps

# Copy code. Build args provide the production env values needed at build time.
COPY . .

# Build — Next.js needs NEXTAUTH_SECRET during page data collection.
ARG NEXTAUTH_SECRET
ARG NEXTAUTH_URL=http://localhost:8010
ARG API_HOST=api:8000

# Configure API base URL for frontend
# Browser cannot use Docker hostname, so convert faim-api:8000 → http://localhost:8000
# Browser calls go through Next.js proxy (/api/v1 → API container internally)
# Use relative path so CORS is never triggered — proxy handles the real host
RUN printf "\nNEXT_PUBLIC_FAIM_API_BASE_URL=/api/v1\n" >> .env

# Generate a temporary build-time .env from the supplied build args.
RUN if [ -n "$NEXTAUTH_SECRET" ]; then \
  printf "NEXTAUTH_SECRET=%s\nNEXTAUTH_URL=%s\n" "$NEXTAUTH_SECRET" "$NEXTAUTH_URL" >> .env; \
  fi

RUN npm run build

# Runner stage
FROM node:22-alpine AS runner
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
