FROM node:24-alpine AS appbuild
WORKDIR /app
COPY ./code/package*.json /app/
RUN npm install
COPY ./code /app/
RUN npm run build

FROM nginx
COPY --from=appbuild /app/dist /usr/share/nginx/html
COPY ./static_config/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./static_config/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY ./static_config/ui /usr/share/nginx/html/config/
