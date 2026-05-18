# ZGF ERP

## 项目概述

ZGF ERP 是一个基于 Flask 的服装工厂 ERP 后端项目，当前版本聚焦以下能力：

- 平台侧系统管理
  包括用户、角色、菜单、工厂、奖励、日志、监控、员工计酬等模块。

- 工厂侧基础资料管理
  包括尺码、颜色、分类等基础数据。

- 工厂侧业务管理
  包括款号、工序、订单、菲、裁床报工、出货等业务模块。

- 认证与个人中心
  包括账号登录、JWT 鉴权、工厂切换、个人资料、密码修改等能力。

当前接口统一挂载在 `/api/v1` 下，Swagger 文档地址为：

```text
/api/v1/docs
```

## 技术栈

- Python 3
- Flask
- Flask-RESTX
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended
- Marshmallow
- MySQL / SQLite

说明：

- 生产或联调环境建议使用 MySQL
- 如果未配置数据库环境变量，项目会自动回退到本地 SQLite：`instance/dev.sqlite3`

## 环境准备

### 依赖安装

```bash
pip install -r requirements.txt
```

### 关键环境变量
项目通过 `.env` 或系统环境变量读取配置，建议至少配置以下内容：

```env
APP_ENV=development
SECRET_KEY=replace_me
JWT_SECRET_KEY=replace_me

DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_NAME=zgf_erp

FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=1
```

补充说明：

- 如果设置了 `DATABASE_URL`，项目会优先使用该连接串
- 如果未设置 `DB_USER / DB_PASSWORD / DB_HOST / DB_NAME`，项目会自动使用 SQLite
- `APP_ENV` 支持：`development`、`testing`、`production`

## 启动项目

### 方式一：直接运行

```bash
python run.py
```

### 方式二：使用 Flask 命令

```bash
flask --app run.py run
```

默认启动参数由环境变量控制：

- `FLASK_HOST`：默认 `0.0.0.0`
- `FLASK_PORT`：默认 `5000`
- `FLASK_DEBUG`：默认 `1`

## 数据初始化

### 当前方案
项目内置的 Python 初始化脚本与种子命令已移除，不再通过代码直接注入初始化数据。

当前初始化改为本地 SQL 方式：

- 数据库表结构：通过 Alembic 迁移创建
- 初始化基础数据：通过根目录下的本地 SQL 文件执行
- 演示数据：不再默认提供

### 初始化 SQL 目录
根目录下会生成本地 SQL 目录：

```text
local_sql_init/
```

说明：

- 该目录用于存放可执行的初始化 SQL
- 该目录已加入 `.gitignore`
- 该目录不会被 Git 跟踪

### SQL 文件分类
建议按文件顺序执行：

```text
00_cleanup_demo_data.sql
01_sys_user_admin.sql
02_sys_menu.sql
03_sys_reward_config.sql
04_refactor_role_scope_fields.sql
```

各文件作用如下：

- `00_cleanup_demo_data.sql`
  清理历史演示工厂、演示账号及其关联业务数据

- `01_sys_user_admin.sql`
  初始化平台管理员账号

- `02_sys_menu.sql`
  初始化系统菜单

- `03_sys_reward_config.sql`
  初始化奖励配置

- `04_refactor_role_scope_fields.sql`
  将角色归属字段从 `factory_id` 迁移为 `scope_type + scope_id`

### 推荐执行顺序

先执行数据库迁移：

```bash
flask db upgrade
```

然后按顺序执行本地 SQL：

1. `00_cleanup_demo_data.sql`
2. `01_sys_user_admin.sql`
3. `02_sys_menu.sql`
4. `03_sys_reward_config.sql`
5. `04_refactor_role_scope_fields.sql`

### 初始化说明

- 当前默认仅保留平台管理员初始化数据
- 外部用户、演示工厂、演示订单等演示数据不再自动注入
- 初始化数据改为 SQL 后，更适合按环境手工控制执行

## 数据库迁移

### 常规迁移流程

```bash
flask db migrate -m "迁移说明"
flask db upgrade
```

### 常见问题
在不同环境中执行 Alembic 迁移时，可能出现以下情况：

- 本地生成的迁移脚本可以执行
- 服务器执行同一份迁移脚本时报错
- 报错原因通常是删除字段前，相关索引、唯一约束或外键没有先清理

典型场景：

- 先执行 `drop_column`
- 但该字段仍被索引引用
- 或仍被唯一约束、外键约束依赖

这类情况下，迁移脚本需要先删除依赖，再删除字段。

### 推荐处理方式

- 生成迁移脚本后，不要默认直接可用，先检查是否存在删列操作
- 如果迁移中包含 `drop_column`，应重点确认该列是否仍被索引、唯一约束或外键依赖
- 如有依赖，应在迁移脚本中先执行 `drop_index`、删除约束，再执行 `drop_column`

### 项目内置检查命令

```bash
flask check-migration --file migrations/versions/xxxx_xxx.py
```

作用：

- 扫描迁移脚本中的 `drop_column`
- 检查目标列是否仍存在索引、唯一约束或外键依赖
- 提前发现“本地能过、服务器失败”的迁移风险

### 迁移建议

- 每次生成迁移脚本后，先人工检查一遍关键变更
- 涉及删列、改索引、改唯一约束的迁移，建议执行一次 `flask check-migration`
- 上线前，优先在接近服务器结构的环境验证一次 `flask db upgrade`

## 常用命令

### 启动与调试

```bash
python run.py
flask --app run.py run
```

### 数据库迁移

```bash
flask db migrate -m "message"
flask db upgrade
flask check-migration --file migrations/versions/xxxx_xxx.py
```

### 编译检查

```bash
python -m compileall app
```

## 接口模块概览

当前 V1 API 按模块拆分如下：

- `auth`
  登录、刷新 token、切换工厂、获取当前用户信息

- `system`
  用户、角色、菜单、工厂、奖励、日志、监控、员工计酬

- `base_data`
  尺码、颜色、分类

- `business`
  款号、工序、订单、菲模板、菲流转、裁床报工、出货

- `profile`
  个人资料、修改密码、个人工厂信息

## 目录结构

```text
ZGF_erp/
├─ app/
│  ├─ api/                 # 接口层
│  │  ├─ common/           # 通用鉴权、分页、响应模型
│  │  └─ v1/               # V1 版本接口
│  ├─ constants/           # 常量定义
│  ├─ models/              # SQLAlchemy 模型
│  │  ├─ auth/
│  │  ├─ system/
│  │  ├─ base_data/
│  │  └─ business/
│  ├─ schemas/             # Marshmallow 入参/出参校验
│  ├─ services/            # 业务服务层
│  ├─ utils/               # 通用工具
│  ├─ commands.py          # Flask CLI 命令
│  ├─ config.py            # 配置读取
│  ├─ extensions.py        # 扩展初始化
│  └─ __init__.py          # 应用工厂
├─ instance/               # 本地 SQLite 等实例文件
├─ logs/                   # 日志目录
├─ migrations/             # Alembic 迁移脚本
├─ local_sql_init/         # 本地初始化 SQL（已忽略 Git 跟踪）
├─ run.py                  # 启动入口
├─ requirements.txt        # 依赖列表
└─ README.md               # 项目说明
```

## 开发约定

### 权限与身份

- 平台内部用户与工厂外部用户使用不同权限上下文
- 平台内部用户不使用“切换工厂”作为默认工作方式
- 外部用户的数据访问依赖当前工厂上下文与角色菜单权限

### 接口文档

- 当前项目使用 Flask-RESTX 维护 Swagger 文档
- 新增接口时，建议同步补齐：
  - `Namespace`
  - 入参模型
  - 返回模型
  - `response` 注解
  - 方法级说明注释

### 数据结构

- 业务结构优先使用显式表结构表达，不建议继续扩大 JSON 字段承载范围
- 涉及统计、筛选、排序、权限控制的数据，优先落为结构化字段或关联表

### 代码调整建议

- 新增业务模块时，优先同步补：
  - 模型
  - schema
  - service
  - API
  - Swagger 注释
  - 权限菜单 SQL

- 涉及权限码新增时，需同步检查：
  - 菜单初始化 SQL
  - 角色菜单分配
  - 接口装饰器 `permission_required`

- 项目内置的 Python 初始化脚本与种子命令已移除，初始化改为本地 SQL 执行

## 当前维护重点

结合当前项目状态，后续开发建议优先关注：

- 持续减少 JSON 存储，补齐结构化表设计
- 继续完善出货、报工等业务主链路
- 持续收敛 Swagger 定义命名，避免模型名冲突
- 保持迁移脚本在本地与服务器环境下的一致可执行性
