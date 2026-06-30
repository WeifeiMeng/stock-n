# Stock N Frontend

前端是一个基于 Vue 3 + Vite 的单页应用，用于查询 N 规则股票池、运行筛选流程、展示买入/止盈/止损价，并支持导出 PDF。

## 技术栈

- Vue 3
- Vite
- npm
- Nginx，生产镜像中托管静态资源并代理后端 API
- html2pdf.js，用于导出 PDF

## 项目结构

```text
frontend/
  src/
    App.vue          主页面组件
    main.js          Vue 入口
    styles.css       全局样式
  index.html         Vite HTML 入口
  package.json       npm 配置和前端版本号
  package-lock.json  npm 锁文件
  vite.config.js     本地开发代理配置
  nginx.conf         生产 Nginx 配置
  Dockerfile         前端镜像构建文件
```

## 版本号

前端镜像版本来自 `package.json` 的 `version` 字段。

当前版本：

```text
0.1.0
```

根目录的 `docker-build.sh` 和 `docker-push.sh` 会自动读取这个版本，默认构建：

```text
stock-calculator-frontend:0.1.0
```

## 本地开发

安装依赖：

```bash
cd frontend
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认访问：

```text
http://localhost:5173
```

开发模式下，`vite.config.js` 会把这些路径代理到 `http://localhost:8000`：

```text
/health
/stock-n
/calculate-price
/api
```

因此本地开发前需要先启动后端服务。

## 生产构建

```bash
cd frontend
npm run build
```

构建产物输出到：

```text
frontend/dist/
```

本地预览构建结果：

```bash
npm run preview
```

## Docker 构建

推荐在项目根目录统一构建：

```bash
./docker-build.sh
```

只构建前端镜像：

```bash
docker build --platform linux/amd64 -t stock-calculator-frontend:0.1.0 ./frontend
```

前端 Dockerfile 使用多阶段构建：

1. `node:22-alpine` 执行 `npm ci` 和 `npm run build`
2. `nginx:alpine` 托管 `dist/` 静态资源
3. 通过 `nginx.conf` 代理后端 API 到 `backend:8000`

## API 说明

页面当前使用的主要接口：

```text
GET /stock-n/{date}
GET /stock-n/filter/stream?date=YYYY-MM-DD
GET /health
```

生产环境中，浏览器请求先到前端 Nginx，再由 Nginx 代理到 Docker Compose 网络里的后端服务：

```text
backend:8000
```

## 常用命令

```bash
npm install
npm run dev
npm run build
npm run preview
```

## 注意事项

- 不要提交 `node_modules/` 和 `dist/`，它们已经在根目录 `.gitignore` 中忽略。
- 修改前端版本时，更新 `package.json` 的 `version` 字段。
- 修改 API 路径时，需要同时检查 `vite.config.js` 和 `nginx.conf`。
