# FileOrganizer 使用指南

AI 驱动的文件整理助手，专为 P 型人格设计。

---

## 快速开始

### 安装

```bash
uv sync
```

### 环境配置

创建 `.env` 文件：

```bash
# LLM 配置（通义千问）
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# 可选配置
LARGE_FILE_THRESHOLD_MB=100      # 大文件阈值
STALE_DAYS_THRESHOLD=180         # 过期文件天数
```

---

## 命令详解

### 1. 扫描目录 `fo scan`

扫描目录，显示文件统计和问题检测。

```bash
fo scan                          # 扫描当前目录
fo scan ~/Downloads              # 扫描指定目录
fo scan ~/Downloads --depth 2    # 限制扫描深度
fo scan --no-hash                # 快速扫描（跳过重复检测）
```

**输出示例：**
```
╭─────────────────── Scan Complete ───────────────────╮
│  Total Files        55                              │
│  Total Directories  0                               │
│  Total Size         3.3 MB                          │
│  Empty Directories  0                               │
╰─────────────────────────────────────────────────────╯

Issues Found:
  Duplicates: 3 groups (wasting 1.2 MB)
  Large Files: 2
  Stale Files: 10
```

---

### 2. 生成报告 `fo report`

生成详细的分析报告，支持 AI 洞察。

```bash
fo report                        # 基础报告
fo report --ai                   # AI 分析报告（需要 API key）
fo report --ai ~/Downloads       # 扫描指定目录
fo report -o my-report.md        # 自定义输出路径
```

**AI 报告内容：**
- 工作模式分析（高峰时段、工作日）
- 文件习惯洞察
- P 型人格特点分析
- 个性化整理建议

---

### 3. 智能整理 `fo clean`

交互式文件整理，支持 AI 智能分组。

#### 3.1 AI 智能整理（推荐）

根据文件名语义，自动按项目/主题分组：

```bash
fo clean --ai                    # 预览 AI 分组方案
fo clean --ai --execute          # 执行 AI 分组
```

**效果示例：**
```
整理前：55 个散乱文件

整理后：
├── 合同审核/        (10个文件)
├── AI助手测试/      (8个文件)
├── NLP文档解析/     (6个文件)
├── 招标项目/        (6个文件)
└── ...
```

#### 3.2 自定义分类方式

使用 `--prompt` 指定分类规则：

```bash
# 按月份分类
fo clean --ai -p "按月份分类，格式：2024年1月、2024年2月"

# 按工作类型分类
fo clean --ai -p "按工作类型分：开发文档、测试记录、会议记录、个人文件"

# 按紧急程度分类
fo clean --ai -p "分成：进行中、已完成、待处理"

# 按客户分类
fo clean --ai -p "按客户/公司名称分类"
```

#### 3.3 按文件类型整理

传统的基于规则的分类：

```bash
fo clean --organize              # 按文件类型分类
```

**分类规则：**
- `.docx` → Documents/Word
- `.xlsx` → Documents/Spreadsheets
- `.jpg/.png` → Images
- `.py/.js` → Code/Python, Code/JavaScript

#### 3.4 其他清理选项

```bash
fo clean --duplicates            # 仅清理重复文件
fo clean --large                 # 仅处理大文件
fo clean --stale                 # 仅处理过期文件
fo clean --empty                 # 仅清理空目录
```

---

## 安全机制

- **默认 dry-run 模式**：所有操作默认只预览，不实际执行
- **确认提示**：执行前需要用户确认
- **备份支持**：删除文件前可自动备份
- **操作日志**：记录所有文件操作，支持回滚

使用 `--execute` 才会实际执行：

```bash
fo clean --ai                    # 仅预览
fo clean --ai --execute          # 实际执行
```

---

## 典型工作流

### 日常整理

```bash
# 1. 先扫描看看情况
fo scan ~/Desktop

# 2. 生成 AI 报告，了解整理建议
fo report --ai ~/Desktop

# 3. 预览 AI 整理方案
fo clean --ai ~/Desktop

# 4. 确认无误后执行
fo clean --ai --execute ~/Desktop
```

### 定期清理下载文件夹

```bash
# 扫描并查看过期文件
fo scan ~/Downloads

# 按时间归档
fo clean --ai -p "按下载月份归档" ~/Downloads --execute
```

---

## 支持的 LLM

FileOrganizer 使用 OpenAI 兼容接口，支持：

| 服务商 | BASE_URL | 模型 |
|--------|----------|------|
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-plus |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |
| OpenAI | `https://api.openai.com/v1` | gpt-4o |

修改 `.env` 中的配置即可切换。

---

## 问题排查

### AI 功能不工作

```bash
# 检查 API key 是否配置
cat .env | grep LLM_API_KEY
```

### 文件移动失败

常见原因：
- 文件正在被其他程序使用（如 Office 文档正在编辑）
- 权限不足

解决：关闭相关程序后重试。

### 查看详细日志

```bash
LOG_LEVEL=DEBUG fo scan ~/Desktop
```

---

## 开发相关

```bash
# 运行测试
uv run pytest

# 类型检查
uv run mypy src/fileorg

# 开发模式运行
uv run fo scan
```

---

*FileOrganizer v0.1.0 - AI-powered file organization for P-type personalities*
