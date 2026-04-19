# Hermes Install（pipx + Git）设计

**日期：** 2026-04-19  
**状态：** Draft v1（已逐段与用户确认）  
**适用平台：** macOS、Windows

---

## 1. 目标与边界

### 1.1 目标

提供一个可安装的工具 `hermes-install`，让用户在 macOS/Windows 上通过 GUI 方式选择目标仓库目录，并完成 Hermes Learning 的预览与安装。

核心目标：

1. 通过 `pipx install git+...` 安装后可直接运行 `hermes-install`。
2. 安装过程为 GUI 交互：目录选择框 + 预览确认弹窗。
3. 目标目录若不是 Git 仓库，自动 `git init`。
4. 模板来源在线拉取固定模板仓库的最新稳定 tag（`vX.Y.Z`）。

### 1.2 边界

- 本版本仅支持 macOS、Windows。
- 仅支持 GUI 路径选择与 GUI 预览确认（不提供终端回退交互）。
- 模板迁移内容为 `MCP + Hooks + Scripts`，与现有迁移规则一致。

### 1.3 非目标

- 不支持 Linux。
- 不支持离线安装模板（必须可访问模板仓库）。
- 不在本版本提供 Homebrew 分发。

---

## 2. 方案与取舍

### 2.1 候选方案

1. **A. 独立安装器入口（最终选择）**
   - 入口命令：`hermes-install`
   - 特点：安装体验独立、职责清晰、可长期演进。

2. **B. migrate.py 外层包装**
   - 复用快，但 CLI/GUI 职责混杂，后续扩展成本更高。

3. **C. 纯 GUI 应用**
   - 体验更“图形化”，但实现与发布成本显著提高。

### 2.2 最终选择

采用 **方案 A**：在同一仓库新增独立安装器入口命令 `hermes-install`，底层复用现有迁移核心逻辑。

---

## 3. 架构设计

### 3.1 组件划分

1. **CLI 入口层**（`hermes_install/cli.py`）
   - 启动交互流程，串联各组件。

2. **模板版本解析层**（`hermes_install/template_source.py`）
   - 在线读取模板仓库 tag 列表，选择语义化版本最高 tag。

3. **模板下载层**（`hermes_install/template_source.py`）
   - 基于选定 tag 下载模板归档并解包到临时目录。

4. **GUI 交互层**（`hermes_install/ui.py`）
   - 系统文件夹选择框。
   - 预览确认弹窗（显示新增/冲突/settings 变更摘要）。

5. **迁移执行层**（`hermes_install/migrator.py`）
   - 调用现有迁移核心（plan/apply）。
   - 自动初始化 Git 仓库（必要时）。

### 3.2 目录与命令入口

- 包入口命令：`hermes-install`
- `pyproject.toml` 配置脚本入口：
  - `hermes-install = hermes_install.cli:main`

---

## 4. 用户流程

1. 用户安装工具（方案 2：Git 直装）：
   - 推荐（稳定）：`pipx install "git+https://github.com/hansen-Mercaso/claude-closed-learning.git@vX.Y.Z"`
   - 开发验证：`pipx install "git+https://github.com/hansen-Mercaso/claude-closed-learning.git@master"`

2. 用户执行：
   - `hermes-install`

3. 安装器动作：
   1) 拉取模板仓库最新稳定 tag。  
   2) 下载并解包模板。  
   3) 弹窗选择目标目录。  
   4) 若目录非 git 仓库，自动 `git init`。  
   5) 构建 preview 结果。  
   6) 弹窗展示 preview 摘要并请求确认。  
   7) 用户确认后 apply，取消则退出。  
   8) 显示成功/失败结果弹窗（失败时包含恢复提示）。

---

## 5. 版本与发布策略

### 5.1 分支与 tag 策略

- 开发分支：`feature/*`
- 发布分支：`master`
- 发布动作：在 `master` 当前提交打 tag（`vX.Y.Z`）并推送。

### 5.2 安装器模板选择规则

- 安装器在线读取模板仓库 tag。
- 仅识别语义化版本 tag（`vX.Y.Z`）。
- 选择最高稳定版本（不包含预发布后缀）。
- 若无任何合法稳定 tag，安装器直接失败并提示“请先在 master 上发布 vX.Y.Z tag”。

### 5.3 回滚策略

- 已发布 tag 视为不可变。
- 回滚通过发布更高 patch 版本实现（如 `v0.1.1`）。

---

## 6. 平台兼容策略（macOS / Windows）

1. GUI 交互使用 `tkinter`（标准库），覆盖文件夹选择和确认弹窗。
2. 路径处理统一使用 `pathlib`。
3. Git 操作调用系统 `git` 可执行。
4. Python 解释器调用使用 `sys.executable` 或显式 `python3/python` 兼容层，避免命令名差异导致失败。

---

## 7. 错误处理

1. **模板仓库不可访问 / 无可用 tag**
   - 直接失败并弹窗提示原因。

2. **目标目录不可写**
   - 失败并提示用户改选目录。

3. **迁移冲突**
   - 在 preview 弹窗中明确展示冲突数量与文件列表。
   - 默认不覆盖；用户可重新选择或取消。

4. **apply 失败**
   - 弹窗显示失败原因与备份路径（若已创建）。

5. **GUI 不可用（tk 初始化失败）**
   - 直接失败并提示“当前环境无法启动图形界面，本版本仅支持 GUI 交互安装”。

---

## 8. 测试与验收

### 8.1 单元测试

1. 语义化 tag 解析与最新版本选择。
2. preview 摘要构建。
3. 非 git 目录自动初始化分支。

### 8.2 集成测试（无 GUI 依赖）

1. 模拟模板下载目录 + 临时目标目录跑 preview/apply。
2. 验证 `scripts/hermes_learning/**` 落盘。
3. 验证 `.claude/settings.json` 合并正确。
4. 验证非 git 目录自动 `git init` 后可继续安装。

### 8.3 手工验收（Win/macOS）

1. `pipx install git+...` 成功。
2. `hermes-install` 可弹文件夹选择框。
3. 预览确认弹窗可取消/确认。
4. 成功后目标仓库配置可用。

---

## 9. 依赖与前置条件

1. 用户机器安装：Python、pipx、git。
2. 目标机器可访问模板仓库。
3. 模板仓库完成 `master + tag` 发布整理：
   - `feature/hermes-learning` 合并到 `master`。
   - 在 `master` 打首个版本 tag（例如 `v0.1.0`）。

---

## 10. 已确认决策清单

1. 分发方式：pipx + Git 直装（方案 2）。
2. 交互方式：GUI 文件夹选择 + GUI 预览确认。
3. 目标平台：macOS + Windows。
4. 非 git 目录处理：自动 `git init`。
5. 模板来源：在线拉取固定模板仓库。
6. 版本规则：从 `master` 发布 tag，安装器拉最新稳定 tag。
