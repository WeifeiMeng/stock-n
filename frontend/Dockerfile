# 使用 Nginx 作为基础镜像
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/nginx:alpine

# 复制前端文件到 Nginx 的默认静态文件目录
COPY *.html /usr/share/nginx/html/

# 使用独立配置文件，便于维护 API 代理
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
