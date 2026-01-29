# ==========================================
# FAIMATRIX: Monolithic Intelligence Build
# ==========================================

FROM node:20-alpine

WORKDIR /app

# 1. Ingest Dependencies
COPY package*.json ./
RUN npm install --legacy-peer-deps

# 2. Absorb Codebase (The entire fractal)
COPY . .

# 3. Generate Intelligence (Production Build)
ARG API_HOST=api:8000
ENV API_HOST=${API_HOST}
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# 4. Ignite
# Using 'npm start' handles all serving logic automatically
EXPOSE 3000
CMD ["npm", "start"]
