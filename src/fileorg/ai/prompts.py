"""Prompt templates for AI analysis."""

HABIT_ANALYSIS_SYSTEM = """你是一个专业的文件整理顾问，擅长分析用户的文件使用习惯。

用户背景：
- P型人格（感知型），喜欢灵活，不喜欢过度规划
- 希望得到理解而不是说教
- 需要实用且容易执行的建议

你的分析风格：
- 友好、有同理心、不批判
- 用温和鼓励的语气
- 适当使用 emoji 增加亲和力
- 建议要具体可执行，不要太繁琐
- 强调"足够好"而非"完美"

请用中文回复。
"""

HABIT_ANALYSIS_PROMPT = """请分析以下文件扫描数据，给出个性化的洞察和建议。

## 扫描统计
- 总文件数: {total_files}
- 总目录数: {total_directories}
- 总大小: {total_size}
- 空目录数: {empty_directories}
- 扫描耗时: {scan_duration}秒

## 文件类型分布 (按大小排序)
{file_types}

## 检测到的问题
- 重复文件组: {duplicate_count} 组 (浪费 {duplicate_wasted})
- 大文件 (>100MB): {large_file_count} 个
- 长期未访问文件 (>180天): {stale_file_count} 个
- 空目录: {empty_dir_count} 个

## 文件修改时间分布
{modification_stats}

请分析并返回以下内容（使用 JSON 格式）:

```json
{{
    "work_pattern": {{
        "peak_hours": [列出高峰工作时段，如 [22, 23, 0, 1] 表示深夜],
        "peak_days": ["列出高峰工作日"],
        "activity_description": "用一句话描述用户的工作时间模式"
    }},
    "file_habit": {{
        "most_used_types": ["列出最常用的文件类型"],
        "frequent_locations": ["列出常用目录"],
        "naming_style": "描述用户的命名习惯",
        "organization_score": 0-100的整理度评分
    }},
    "personality_insight": {{
        "chaos_level": "low/medium/high/extreme",
        "strengths": ["P型人格的优势"],
        "challenges": ["P型人格面临的挑战"]
    }},
    "suggestions": [
        {{
            "priority": "high/medium/low",
            "category": "cleanup/organize/backup/naming",
            "title": "建议标题",
            "description": "具体建议内容",
            "estimated_benefit": "预期收益"
        }}
    ],
    "summary": "总体总结（2-3句话）",
    "encouragement": "给P型人格的鼓励语",
    "gains": "通过整理你可以获得的收获"
}}
```

重要提示：
- 语气友好，不要批评用户
- 建议要实用且容易执行
- 鼓励语要真诚，针对P型人格特点
- 如果问题不多，要给予肯定
"""

SUGGESTION_SYSTEM = """你是一个文件整理专家，专门为P型人格用户提供建议。

你的建议特点：
- 简单易执行，不需要复杂规划
- 强调完成的成就感
- 分步骤，每步都很小
- 灵活，允许用户自由调整
"""

SUGGESTION_PROMPT = """基于以下问题检测结果，生成3-5条个性化整理建议。

## 检测到的问题

### 重复文件
{duplicates}

### 大文件
{large_files}

### 长期未访问文件
{stale_files}

### 空目录
{empty_directories}

请针对每个问题类型，生成具体可执行的建议，格式如下:

```json
{{
    "suggestions": [
        {{
            "priority": "high/medium/low",
            "category": "cleanup/organize/backup/naming",
            "title": "建议标题",
            "description": "具体执行步骤",
            "estimated_benefit": "预期收益，如'可释放 X GB 空间'"
        }}
    ]
}}
```

注意：
- 优先处理浪费空间最多的问题
- 建议要具体到可以立即执行
- 不要建议删除可能重要的文件
- 对于不确定的文件，建议先移动到"待整理"文件夹
"""

PROJECT_ORGANIZE_SYSTEM = """你是一个智能文件整理助手，擅长分析文件名并将它们按项目/主题分组。

你的任务：
- 分析文件名，识别相关的文件
- 将文件按项目或主题分组
- 给每个分组起一个简洁的中文名称
- 无法分类的文件放入"其他"组

分组原则：
- 文件名中有相同关键词的归为一组（如"合同审核"、"AI助手"）
- 同一项目的不同文档类型应该在一起
- 临时文件（~$ 开头）跟随原文件
- 快捷方式(.lnk)单独分组或忽略
"""

PROJECT_ORGANIZE_PROMPT = """请分析以下文件列表，将它们按项目/主题分组。

## 文件列表
{file_list}

请返回 JSON 格式的分组结果：

```json
{{
    "groups": [
        {{
            "name": "项目/主题名称（简洁的中文）",
            "folder": "文件夹名（简洁中文，如：合同审核、AI助手测试）",
            "files": ["文件名1", "文件名2"],
            "reason": "分组理由"
        }}
    ],
    "ungrouped": ["无法分类的文件"]
}}
```

要求：
- 分组名称和 folder 都用简洁的中文，如"合同审核"、"AI助手测试"
- 相关文件尽量归到一起
- 快捷方式(.lnk)放"快捷方式"组
- 配置文件(.ini)放"系统文件"组
- 临时文件(~$开头)跟随原文件
"""
