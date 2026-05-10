# 医疗影像智能分析系统安装指南

本文档提供详细的安装步骤，帮助您成功部署和运行医疗影像智能分析与预约管理系统。

## 系统要求

### 硬件要求
- CPU: 双核处理器及以上
- 内存: 至少4GB RAM (推荐8GB或更高)
- 硬盘: 至少20GB可用空间
- 显卡: 如需运行AI诊断模型，建议NVIDIA GPU (4GB+内存)

### 软件要求
- 操作系统: Windows 10/11, Linux (Ubuntu 18.04+), macOS
- Python 3.8+
- MySQL 5.7+
- Node.js 14+ 和 npm 6+
- Git（可选，用于克隆代码）

## 详细安装步骤

### 1. 环境准备

#### Windows 系统
1. **安装 Python**:
   - 从 [Python官网](https://www.python.org/downloads/) 下载 Python 3.8+
   - 安装时勾选"Add Python to PATH"
   - 验证安装: `python --version`

2. **安装 MySQL**:
   - 从 [MySQL官网](https://dev.mysql.com/downloads/installer/) 下载安装程序
   - 选择"Custom"安装，安装 MySQL Server 和 Workbench
   - 记住设置的 root 密码
   - 验证安装: 使用 MySQL Workbench 连接

3. **安装 Node.js**:
   - 从 [Node.js官网](https://nodejs.org/) 下载 LTS 版本
   - 完成安装后验证: `node -v` 和 `npm -v`

#### Linux 系统
```bash
# 安装 Python
sudo apt update
sudo apt install python3.8 python3.8-venv python3-pip

# 安装 MySQL
sudo apt install mysql-server mysql-client

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_14.x | sudo -E bash -
sudo apt install nodejs
```

### 2. 获取项目代码

```bash
# 克隆项目
git clone <项目仓库地址>
cd medical-imaging-system

# 或解压下载的ZIP包
unzip medical-imaging-system.zip
cd medical-imaging-system
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# Windows 激活虚拟环境
venv\Scripts\activate

# Linux/Mac 激活虚拟环境
source venv/bin/activate
```

### 4. 安装依赖

```bash
# 更新 pip
python -m pip install --upgrade pip

# 安装 Python 依赖
pip install -r requirements.txt

# 如果遇到依赖问题，可以单独安装核心包
pip install flask flask-sqlalchemy flask-login flask-session pymysql pandas numpy SimpleITK scikit-image
```

### 5. 配置数据库

1. **创建数据库**:
```sql
CREATE DATABASE medical_imaging_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **配置数据库连接**:
   编辑 `config.py` 或 `.env` 文件：
```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://用户名:密码@localhost:3306/medical_imaging_system'
```

3. **初始化数据库**:
```bash
python db_model.py
```

### 6. 前端构建

```bash
# 进入 Vue 项目目录
cd vue/medical_vue

# 安装依赖
npm install --ignore-scripts

# 构建项目
npm run build

# 如果构建失败，尝试：
node_modules\.bin\webpack.cmd --config build/webpack.dev.config.js  # Windows
./node_modules/.bin/webpack --config build/webpack.dev.config.js    # Linux/Mac
```

### 7. 启动应用

```bash
# 返回项目根目录
cd ../..

# 启动 Flask 应用
python app.py
```

应用将在 http://localhost:5002 启动

## 开发模式运行

```bash
# 启动后端（开发模式）
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development    # Windows
python app.py

# 启动前端开发服务器（新终端）
cd vue/medical_vue
npm run dev
```

## 常见问题解决

### 1. 数据库连接问题
- 确认 MySQL 服务运行状态
- 验证数据库用户名和密码
- 检查数据库名称是否正确
- 确保已安装 pymysql：`pip install pymysql`

### 2. 依赖安装问题
```bash
# 如果遇到模块导入错误
pip install -r requirements.txt --upgrade

# 或手动安装缺失模块
pip install <模块名>
```

### 3. Vue 构建问题
- 确保 Node.js 版本 >= 14.0.0
- 清除 npm 缓存：`npm cache clean --force`
- 重新安装依赖：
```bash
rm -rf node_modules
npm install --ignore-scripts
```

### 4. Windows 特定问题
- Python 命令未识别：使用 `py` 替代 `python`
- 检查环境变量设置
- 可能需要安装 Visual C++ Build Tools

## 生产环境部署

### 1. 安全配置
- 修改 `config.py` 中的密钥
- 启用 HTTPS
- 配置防火墙规则
- 设置适当的文件权限

### 2. 使用 Gunicorn（Linux）
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 app:app
```

### 3. 配置 Nginx（可选）
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. 配置 Supervisor（可选）
```ini
[program:medical_imaging]
directory=/path/to/project
command=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5002 app:app
autostart=true
autorestart=true
stderr_logfile=/var/log/medical_imaging/err.log
stdout_logfile=/var/log/medical_imaging/out.log
```

## 系统维护

### 1. 数据库备份
```bash
# 创建备份
mysqldump -u root -p medical_imaging_system > backup.sql

# 恢复备份
mysql -u root -p medical_imaging_system < backup.sql
```

### 2. 日志管理
- 检查 `logs` 目录下的应用日志
- 定期归档旧日志
- 配置日志轮转

### 3. 系统更新
```bash
# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt --upgrade

# 更新数据库（如果有变更）
python db_model.py

# 重新构建前端
cd vue/medical_vue
npm install
npm run build
```

## 故障排除

### 1. 应用无法启动
- 检查端口占用情况
- 查看错误日志
- 验证配置文件

### 2. 数据库连接失败
- 检查 MySQL 服务状态
- 验证连接字符串
- 确认用户权限

### 3. 前端资源加载失败
- 检查构建输出目录
- 验证静态文件配置
- 清除浏览器缓存
