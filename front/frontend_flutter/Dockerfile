# Build stage - Usando la imagen oficial de Flutter más reciente
FROM ghcr.io/cirruslabs/flutter:latest AS build

# Configurar como no-root para evitar warnings
USER root

WORKDIR /app

# Copiar archivos de configuración
COPY pubspec.yaml ./

# Instalar dependencias (sin copiar pubspec.lock para evitar conflictos)
RUN flutter pub get

# Copiar código fuente
COPY . .

# Build para web
RUN flutter build web --release

# Runtime stage
FROM nginx:alpine

# Copiar archivos compilados
COPY --from=build /app/build/web /usr/share/nginx/html

# Configuración nginx para SPA
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]