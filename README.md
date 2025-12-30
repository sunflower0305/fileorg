# FileOrganizer (fo)

> **AI 驱动的文件整理助手，专为"懒人"设计**
>
> 你是不是桌面堆满文件却不想整理？下载文件夹塞了几百个却懒得分类？
>
> FileOrganizer 让 AI 帮你搞定一切。

---

## 效果展示

**整理前：** 桌面 55 个散乱文件

**整理后：**
```
Desktop/
├── 合同审核/        (10个文件) - AI 识别出合同相关文档
├── AI助手测试/      (8个文件)  - Q&A记录、测试表格自动归类
├── NLP文档解析/     (6个文件)  - 技术方案、架构图归为一组
├── 招标项目/        (6个文件)  - 招标公告、报价单自动关联
├── 个人简历/        (2个文件)  - 简历和证件照放一起
└── ...
```

**一行命令，52 个文件自动归位。**

---

## 特色功能

### 1. AI 智能分组

不是简单按文件类型分类，而是**理解文件名语义**：

```bash
fo clean --ai ~/Desktop
```

AI 会识别出：
- `合同审核知识库.md` + `合同模板.docx` → **合同审核/**
- `Q&A测试记录.xlsx` + `ai助手问答.csv` → **AI助手测试/**

### 2. 自定义分类规则

告诉 AI 你想怎么分：

```bash
# 按月份归档
fo clean --ai -p "按月份分类" ~/Downloads

# 按客户分类
fo clean --ai -p "按客户名称分类" ~/Documents

# 按项目阶段分类
fo clean --ai -p "分成：进行中、已完成、待处理" ~/Desktop
```

### 3. AI 习惯分析

生成个性化报告，了解你的文件使用习惯：

```bash
fo report --ai ~/Desktop
```

输出：
```
工作模式：周一、周五下午活跃
组织评分：85/100
AI 建议：
  1. 创建 3 个文件夹分类整理
  2. 启用自动备份
  3. 尝试轻量级命名约定
```

### 4. 安全第一

- **默认 dry-run**：先预览，确认后再执行
- **操作可回滚**：所有移动都有记录
- **备份保护**：删除前自动备份

---

## 快速开始

### 安装

```bash
git clone https://github.com/yourname/fileorg.git
cd fileorg
uv sync
```

### 配置 AI（可选）

创建 `.env` 文件：

```bash
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

支持通义千问、DeepSeek、OpenAI 等兼容接口。

### 使用

```bash
# 扫描目录
fo scan ~/Desktop

# AI 智能整理（预览）
fo clean --ai ~/Desktop

# 确认后执行
fo clean --ai --execute ~/Desktop
```

---

## 命令速查

| 命令 | 说明 |
|------|------|
| `fo scan` | 扫描目录，显示统计和问题 |
| `fo report --ai` | 生成 AI 分析报告 |
| `fo clean --ai` | AI 智能分组（预览） |
| `fo clean --ai --execute` | AI 智能分组（执行） |
| `fo clean --ai -p "规则"` | 自定义分类规则 |
| `fo clean --organize` | 按文件类型分类 |

---

## 为什么选择 FileOrganizer？

| 传统整理工具 | FileOrganizer |
|-------------|---------------|
| 按扩展名分类 (.docx → Word/) | AI 理解语义 (合同.docx → 合同审核/) |
| 需要手动制定规则 | 自然语言描述，AI 自动理解 |
| 机械式分类 | 识别项目关系，关联文件归组 |
| 冷冰冰的工具 | P 型人格友好，鼓励式提示 |

---

## 技术栈

- **CLI**: Typer + Rich（漂亮的命令行界面）
- **AI**: OpenAI 兼容接口（通义千问/DeepSeek/GPT）
- **异步**: asyncio（快速扫描大目录）
- **类型安全**: Pydantic + mypy

---

## 开发

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest

# 类型检查
uv run mypy src/fileorg
```

---

## License

MIT

---

**如果这个工具帮到了你，欢迎 Star ⭐**
