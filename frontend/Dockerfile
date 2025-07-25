# Multi-stage build for Car Auction Analyzer Frontend
# Stage 1: Build the React application
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Add package files
COPY package.json package-lock.json* ./

# Install dependencies with cache optimization
RUN npm ci --no-audit --no-fund

# Copy application source
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve the application with nginx
FROM nginx:alpine

# Copy the build output from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration if needed
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create a non-root user to run nginx
RUN adduser -D -H -u 1001 -s /sbin/nologin -G nginx nginx-user && \
    chown -R nginx-user:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Support for environment variables at runtime
# Create a script to replace environment variables in the JS files
RUN apk add --no-cache bash
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Switch to non-root user
USER nginx-user

# Use the entrypoint script to enable environment variable substitution
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
