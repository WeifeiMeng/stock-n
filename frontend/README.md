# 股票价格计算器 - 前端应用

一个简单美观的Web应用，用于输入股票价格并调用后端API计算买入价位和止损价。

## 功能特性

- 🎨 现代化的UI设计
- 📱 响应式布局，支持移动设备
- ⚡ 实时计算买入价位（买一价、买二价、买三价）
- 📊 显示止损价格和止损幅度
- ✅ 输入验证和错误处理

## 使用方法

### 1. 确保后端API正在运行

首先，确保后端API服务器正在运行：

```bash
cd backend
uv run python3 main.py
```

后端API应该在 `http://localhost:8000` 运行。

### 2. 打开前端应用

有两种方式打开前端应用：

#### 方式一：直接在浏览器中打开

双击 `index.html` 文件，或在浏览器中打开：
```bash
open index.html  # macOS
# 或
xdg-open index.html  # Linux
```

#### 方式二：使用本地服务器（推荐）

使用Python内置服务器：
```bash
cd frontend
python3 -m http.server 8080
```

然后在浏览器中访问：`http://localhost:8080`

### 3. 使用应用

1. 在输入框中输入当前股票价格（例如：100）
2. 点击"计算买入价位"按钮或按回车键
3. 查看计算结果，包括：
   - 当前价格
   - 买一价、买二价、买三价
   - 每个价位的止损价格和止损幅度

## 技术栈

- HTML5
- CSS3（使用现代CSS特性，包括Grid和Flexbox）
- 原生JavaScript（ES6+）
- Fetch API用于HTTP请求

## API端点

前端应用调用后端API的 `/calculate` 端点：

- **URL**: `http://localhost:8000/calculate`
- **方法**: POST
- **请求体**:
  ```json
  {
    "current_price": 100.0
  }
  ```

## 注意事项

- 确保后端API在 `http://localhost:8000` 运行
- 如果遇到CORS错误，可能需要配置后端允许跨域请求
- 输入的价格必须大于0

## 故障排除

### 如果遇到"请求失败"错误：

1. 检查后端API是否正在运行
2. 确认后端API地址是否为 `http://localhost:8000`
3. 检查浏览器控制台是否有错误信息

### 如果遇到CORS错误：

需要在后端添加CORS中间件。可以在 `backend/main.py` 中添加：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
