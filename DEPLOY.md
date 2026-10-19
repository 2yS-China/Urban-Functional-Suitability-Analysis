# 城市片区功能适宜性分析系统 - 部署指南

## 系统概述

本系统用于城市片区功能适宜性分析，包含：
- **后端 API 服务**：基于 FastAPI，处理空间分析、知识图谱、智能问答
- **前端应用**：静态 HTML/JS/CSS，提供可视化地图和交互界面

## 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10/11, macOS, Linux | Windows 11 |
| Python | 3.9+ | 3.10 或 3.11 |
| 磁盘空间 | 500MB | 1GB+ |
| 内存 | 4GB | 8GB+ |

---

## 第一步：安装 Python

### Windows

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.10 或 3.11 安装包
3. 运行安装程序，**务必勾选** "Add Python to PATH"
4. 点击 "Install Now" 完成安装

验证安装：
```bash
python --version
# 应显示 Python 3.10.x 或 3.11.x
```

### macOS

```bash
# 安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.10
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
```

---

## 第二步：下载项目文件

将整个项目文件夹复制到目标电脑，确保目录结构如下：

```
城市片区功能适宜性分析/
├── backend/
│   ├── api/
│   ├── data_processor/
│   ├── kg/
│   ├── spatial_analysis/
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── app.js
│   ├── index.html
│   ├── styles.css
│   └── ...
├── start.bat          # Windows 启动脚本
└── 启动系统.bat       # Windows 启动脚本（中文）
```

---

## 第三步：安装 GDAL（关键依赖）

GDAL 是处理地理空间数据的核心库，需要单独安装。

### Windows

```bash
# 推荐使用 conda 或下载预编译包
pip install GDAL==3.6.2

# 如果上面的命令失败，下载预编译的 wheel 文件：
# 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
# 下载对应 Python 版本的 .whl 文件，然后：
pip install GDAL-3.6.2-cp310-cp310-win_amd64.whl
```

### macOS

```bash
brew install gdal
pip install GDAL==$(gdal-config --version)
```

### Linux

```bash
sudo apt install libgdal-dev gdal-bin
pip install GDAL==$(gdal-config --version)
```

---

## 第四步：安装 Python 依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 常见问题处理

如果 `rtree` 安装失败：
```bash
# Windows: 安装 Visual C++ Build Tools
# 或使用 conda:
conda install -c conda-forge rtree
```

如果 `shapely` 安装失败：
```bash
pip install shapely --no-binary shapely
```

---

## 第五步：配置说明

系统配置文件位于 `backend/config/` 目录。默认配置即可运行，如需修改：

```yaml
# backend/config/default.yaml
server:
  host: "0.0.0.0"
  port: 8000

data:
  upload_dir: "data/uploads"
  result_dir: "data/results"
```

---

## 第六步：启动系统

### 方式一：使用启动脚本（推荐）

**Windows：**
- 双击 `启动系统.bat` 或 `start.bat`

**macOS/Linux：**
```bash
# 终端1：启动后端
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动前端
cd frontend
python -m http.server 8080
```

### 方式二：手动启动

```bash
# 终端1：后端服务
cd backend
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：前端服务
cd frontend
python -m http.server 8080
```

---

## 第七步：访问系统

启动成功后，打开浏览器访问：

| 服务 | 地址 |
|------|------|
| **前端应用** | http://localhost:8080 |
| **后端 API** | http://localhost:8000 |
| **API 文档** | http://localhost:8000/docs |

---

## 数据格式要求

### 矢量数据（边界、POI、路网等）

支持格式：`.geojson`, `.json`, `.zip`（Shapefile 压缩包）

GeoJSON 示例：
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [113.3, 23.1]
      },
      "properties": {
        "name": "示例POI",
        "category": "餐饮"
      }
    }
  ]
}
```

### 栅格数据（DEM、土地利用等）

支持格式：`.tif`, `.tiff`

要求：
- 坐标系：WGS-84 (EPSG:4326)
- 数据类型：浮点型或整型

---

## 常见问题排查

### 1. 端口被占用

```bash
# Windows 查看占用端口
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### 2. GDAL 导入错误

```
ImportError: DLL load failed
```
解决方案：安装 Visual C++ Redistributable
下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe

### 3. 地图无法显示

检查网络连接，高德地图瓦片需要互联网访问。

### 4. 文件上传失败

检查 `backend/data/uploads/` 目录是否存在，确保有写入权限。

### 5. 分析任务卡住

检查后端终端输出，查看是否有错误日志。常见原因：
- 数据格式不正确
- 内存不足

---

## 打包清单

部署时需要复制的文件/文件夹：

```
✓ backend/              # 后端代码和依赖
✓ frontend/             # 前端静态文件
✓ start.bat             # 启动脚本
✓ 启动系统.bat          # 启动脚本（中文）
✓ DEPLOY.md             # 本文档
```

不需要复制的文件：
```
✗ .git/                 # Git 版本控制
✗ __pycache__/          # Python 缓存
✗ node_modules/         # 无 Node.js 依赖
✗ venv/                 # 虚拟环境（需重新创建）
```

---

## 快速部署脚本

将以下内容保存为 `快速部署.bat`，可在新电脑上一键安装：

```batch
@echo off
chcp 65001 >nul
echo ========================================
echo 城市片区功能适宜性分析系统 - 快速部署
echo ========================================
echo.

echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       Python 已安装

echo [2/4] 创建虚拟环境...
cd backend
if not exist venv (
    python -m venv venv
    echo       虚拟环境创建完成
) else (
    echo       虚拟环境已存在
)

echo [3/4] 激活环境并安装依赖...
call venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 部分依赖安装失败，请检查错误信息
)

echo [4/4] 安装 GDAL...
pip install GDAL
if errorlevel 1 (
    echo 警告: GDAL 安装失败，请参考 DEPLOY.md 手动安装
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 使用方法: 双击 "启动系统.bat" 启动服务
echo.
pause
```

---

## 技术支持

如遇到问题，请提供：
1. 操作系统版本
2. Python 版本 (`python --version`)
3. 完整的错误信息
4. 后端终端的日志输出

---

## 版本信息

- 系统版本：v1.0
- 更新日期：2026-03-20