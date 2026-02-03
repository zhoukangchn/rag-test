import os
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.app.agents.warroom_graph import warroom_agent

def save_graph_visualization():
    """将 Warroom Agent 的流程图保存为图片"""
    try:
        # 获取 Mermaid 图并在本地保存
        png_data = warroom_agent.get_graph().draw_mermaid_png()
        output_path = "docs/images/warroom_graph.png"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        print(f"✅ 流程图已保存至: {output_path}")
        
        # 同时打印 Mermaid 文本，以防图片生成失败
        print("\n--- Mermaid Code ---")
        print(warroom_agent.get_graph().draw_mermaid())
        
    except Exception as e:
        print(f"❌ 无法生成流程图: {e}")
        print("\n--- 尝试输出 Mermaid 文本 ---")
        try:
            print(warroom_agent.get_graph().draw_mermaid())
        except:
            print("无法获取 Mermaid 文本")

if __name__ == "__main__":
    save_graph_visualization()
