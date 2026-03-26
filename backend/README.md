# 股票价格计算API

一个基于FastAPI的股票价格计算服务，提供买一价、买二价、买三价及其对应的止损价计算。

## 功能特性

- 计算三个买入价位（1.04倍、1.03倍、1.02倍当前价格）
- 为每个买入价位计算对应的止损价（95%的买入价）
- 自动验证输入数据
- 提供结构化的JSON响应

## 安装和运行

### 使用uv（推荐）

```bash
# 安装依赖
uv sync

# 运行API服务器
uv run python3 main.py
```

### 手动安装

```bash
# 安装依赖
pip install -e .

# 运行API服务器
python3 main.py
```

服务器将在 `http://localhost:8000` 启动。

## MySQL 中间件配置

后端已内置 MySQL Session 中间件（请求级别自动创建/提交/回滚会话）。

可任选其一配置方式：

1) 单变量 DSN（推荐）

```bash
MYSQL_DSN=mysql+aiomysql://user:password@127.0.0.1:3306/your_db
```

2) 分项变量

```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=user
MYSQL_PASSWORD=password
MYSQL_DATABASE=your_db
```

未配置上述变量时，服务仍可启动，但不会启用 MySQL 连接。

## API端点

### GET /

获取API基本信息。

**响应示例：**
```json
{
  "message": "股票价格计算API",
  "version": "1.0.0"
}
```

### GET /health

健康检查端点。

**响应示例：**
```json
{
  "status": "healthy"
}
```

### POST /calculate

计算股票买入价和止损价。

**请求体：**
```json
{
  "current_price": 100.0
}
```

**响应示例：**
```json
{
  "current_price": 100.0,
  "buy_levels": [
    {
      "level": "买一价",
      "buy_price": 104.0,
      "stop_loss_price": 98.8,
      "stop_loss_percentage": 5.0
    },
    {
      "level": "买二价",
      "buy_price": 103.0,
      "stop_loss_price": 97.85,
      "stop_loss_percentage": 5.0
    },
    {
      "level": "买三价",
      "buy_price": 102.0,
      "stop_loss_price": 96.9,
      "stop_loss_percentage": 5.0
    }
  ]
}
```

## 测试API

### 使用curl测试

```bash
# 测试健康检查
curl http://localhost:8000/health

# 计算价格（价格=100）
curl -X POST "http://localhost:8000/calculate" \
  -H "Content-Type: application/json" \
  -d '{"current_price": 100}'
```

### 使用Python测试

```python
import requests

# 计算股票价格
response = requests.post(
    "http://localhost:8000/calculate",
    json={"current_price": 100}
)
print(response.json())
```

## 错误处理

API会对无效输入进行验证：

- `current_price` 必须是正数
- 输入必须是有效的JSON格式

**错误响应示例：**
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "current_price"],
      "msg": "Input should be greater than 0",
      "input": -10,
      "ctx": {"gt": 0.0}
    }
  ]
}
```
