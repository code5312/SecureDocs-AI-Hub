FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS runner
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S app \
    && adduser -S app -G app \
    && chown app:app /app
COPY --from=deps --chown=app:app /app/node_modules ./node_modules
COPY --chown=app:app . .
RUN mkdir -p /app/.next \
    && chown -R app:app /app/.next
USER app
EXPOSE 3000
CMD ["npm", "run", "dev"]
