# 使用 Nginx 作为基础镜像
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/nginx:alpine

# 复制前端文件到 Nginx 的默认静态文件目录
COPY index.html /usr/share/nginx/html/

# 创建自定义 Nginx 配置文件以处理 SPA 和 API 代理
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # 前端静态文件 \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # API 代理到后端 \
    location /api/ { \
        proxy_pass http://backend:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
