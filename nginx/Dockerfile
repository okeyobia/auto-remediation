FROM nginx:latest

# Copy custom nginx config with stub_status enabled
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
