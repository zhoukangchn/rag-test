"""Prompt 模板定义"""

import os
from pathlib import Path

# Base directory for prompts (project root/prompts)
PROMPTS_DIR = (Path(__file__).resolve() / ".." / ".." / ".." / ".." / "prompts").resolve()


def _load_prompt(filename: str) -> str:
    """从 Markdown 文件加载提示词模板"""
    filepath = PROMPTS_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# 检查节点 (Check Node)
CHECK_PROMPT_REFLECTION = _load_prompt("check_prompt_reflection.md")
CHECK_PROMPT_DEFAULT = _load_prompt("check_prompt_default.md")

# 检索节点 (Retrieve Node)
REFINE_PROMPT = _load_prompt("refine_prompt.md")

# 生成节点 (Generate Node)
GENERATE_SYSTEM_PROMPT_BASE = _load_prompt("generate_system_prompt_base.md")
GENERATE_SYSTEM_PROMPT_KNOWLEDGE = _load_prompt("generate_system_prompt_knowledge.md")
GENERATE_SYSTEM_PROMPT_REFLECTION = _load_prompt("generate_system_prompt_reflection.md")

# 反思节点 (Reflect Node)
REFLECT_PROMPT = _load_prompt("reflect_prompt.md")
