# SunuDoctor frontend — production image served by nginx.
#
# Build context: ./frontend
#   docker build -t sunudoctor-web ./frontend \
#     --build-arg VITE_API_BASE=https://api.example.sn/api
#
# The API base is injected at build time. With no value the app calls /api on
# the same origin (the nginx config proxies /api to the backend service).
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build


FROM nginx:1.27-alpine AS runtime

# Replace the default site with our SPA + API proxy config.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/sunudoctor.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
