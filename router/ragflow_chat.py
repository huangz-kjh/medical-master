import os
import json
import requests
import logging
import argparse
from pathlib import Path
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RAGFlow配置
RAGFLOW_URL = "https://u638277-9c20-f3631990.cqa1.seetacloud.com:8443"
CHAT_ASSISTANT_ID = "3cabe0223a5c11f0a9540242ac110003"
RAGFLOW_API_KEY = "ragflow-djNjA3YjhhM2I2ZDExZjA4ZDg5MDI0Mm"

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {str(e)}")
        return None

def chat_with_ragflow(message, conversation_id=None, is_new=False):
    """与RAGFlow聊天"""
    try:
        headers = {
            "Authorization": f"Bearer {RAGFLOW_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "model",
            "messages": [{"role": "user", "content": message}],
            "stream": True
        }
        
        url = f"{RAGFLOW_URL}/api/v1/chats_openai/{CHAT_ASSISTANT_ID}/chat/completions"
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False,
            stream=True
        )
        
        response.raise_for_status()
        
        # 处理流式响应
        full_response = ""
        current_section = ""
        sections = []
        processed_content = set()  
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        if data.get('choices') and data['choices'][0].get('delta', {}).get('content'):
                            content = data['choices'][0]['delta']['content']
                            content = content.replace('<think>', '').replace('</think>', '')
                            content = re.sub(r'<\|.*?\|>', '', content)
                            content = re.sub(r'(k>|n>|in>|thin>)+', '', content)
                            content = ' '.join(content.split())
                            current_section += content
                                
                    except json.JSONDecodeError:
                        continue
        
        if current_section:
            sections.append(current_section.strip())
        
        full_content = "\n".join(sections)
        cleaned_content = full_content.strip()
        
        # 提取"医疗报告："之后和"> 1."之前的内容
        match = re.search(r'^(.*?)(?=>\s*1\.)', cleaned_content, re.DOTALL)
        if match:
            cleaned_content = match.group(1).strip()
        match = re.search(r'医疗报告：(.*?)$', cleaned_content, re.DOTALL)
        if match:
            cleaned_content = match.group(1).strip()
        
        # 基础清理
        cleaned_content = re.sub(r'##\d+\$\$', '', cleaned_content)
        cleaned_content = re.sub(r'## [ij]\$\$', '', cleaned_content)
        cleaned_content = re.sub(r'#+\s*', '', cleaned_content)
        cleaned_content = re.sub(r'\*\*', '', cleaned_content)
        cleaned_content = re.sub(r'([，。！？；：])\1+', r'\1', cleaned_content)
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)        
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)        
        cleaned_content = re.sub(r'([。！？])\s*([^-\n])', r'\1\n\n\2', cleaned_content)
        cleaned_content = re.sub(r'<\|.*?\|>.*?<\|.*?\|>', '', cleaned_content)
        cleaned_content = re.sub(r'\*\*Final.*?\*\*', '', cleaned_content)
        cleaned_content = re.sub(r'\*\*Analysis.*?\*\*', '', cleaned_content)
        cleaned_content = re.sub(r'-\s*', '', cleaned_content)
        cleaned_content = re.sub(r'\n\s*\n', '\n', cleaned_content)
        
        # 增强清理流式标记和多余符号
        cleaned_content = re.sub(r'[>]+', '', cleaned_content)
        cleaned_content = re.sub(r'(n|thin|in|k|nthin|thinnngwithith|thenewinformationn)+', '', cleaned_content, flags=re.IGNORECASE)
        cleaned_content = re.sub(r'/thin', '', cleaned_content, flags=re.IGNORECASE)
        cleaned_content = re.sub(r'\\n', '', cleaned_content)
        cleaned_content = re.sub(r'\\t', '', cleaned_content)
        cleaned_content = re.sub(r'\\r', '', cleaned_content)
        cleaned_content = re.sub(r'\\', '', cleaned_content)
        cleaned_content = re.sub(r'\\s+', ' ', cleaned_content)
        cleaned_content = cleaned_content.strip()
        
        # 移除重复内容
        sentences = cleaned_content.split('。')
        unique_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in processed_content:
                processed_content.add(sentence)
                unique_sentences.append(sentence)
        
        cleaned_content = '。'.join(unique_sentences) + '。'
        
        paragraphs = cleaned_content.split('\n\n')
        unique_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph and paragraph not in processed_content:
                processed_content.add(paragraph)
                unique_paragraphs.append(paragraph)
        
        cleaned_content = '\n\n'.join(unique_paragraphs)
        cleaned_content = re.sub(r'请生成.*?报告：', '', cleaned_content)
        cleaned_content = re.sub(r'以下是.*?报告：', '', cleaned_content)
        cleaned_content = re.sub(r'根据.*?报告：', '', cleaned_content)
    
        return {
            "response": cleaned_content,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"RAGFlow聊天失败: {str(e)}")
        return None

def process_file(file_path):
    """处理指定的文件"""
    logger.info(f"处理文件: {file_path}")
    
    content = read_file_content(file_path)
    if not content:
        return None
    
    # 添加提示词
    prompt = f"""请生成一份医疗报告，要求：
1. 使用纯文本格式，不要使用markdown标记
2. 内容要连贯，不要分段太多
3. 不要使用引用标记和特殊符号
4. 按照以下结构组织内容：
   - 临床分析（症状关联、鉴别诊断、功能影响）
   - 诊断建议（治疗方案、注意事项、预后评估）
   - 后续随访建议（影像学随访、功能评估、症状管理）

诊断信息：
{content}"""
        
    # 发送到RAGFlow
    response = chat_with_ragflow(prompt)
    if response:
        return {
            "file": file_path,
            "response": response["response"]
        }
    return None

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理指定的txt文件并获取RAGFlow回复')
    parser.add_argument('file_path', help='要处理的txt文件路径')
    args = parser.parse_args()
    
    # 处理文件
    result = process_file(args.file_path)
    
    # 输出结果
    if result:
        print("\n" + "="*50)
        print(f"文件: {result['file']}")
        print("-"*50)
        print(f"RAGFlow回复:\n{result['response']}")
        print("="*50)
    else:
        print("处理文件失败")

if __name__ == "__main__":
    main() 