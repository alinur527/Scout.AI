FROM node:22-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY LICENSE NOTICE /app/
COPY docs/THIRD_PARTY_NOTICES.md /app/docs/THIRD_PARTY_NOTICES.md
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:1.28-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
