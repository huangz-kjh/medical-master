import http.client
import json
import os
import random
import re
import string
from datetime import datetime

import dashscope
import requests
from flask import Response, request, jsonify, render_template, session, Blueprint, current_app
from werkzeug.utils import secure_filename
import logging
from db_model import db, ChatSession, ChatMessage, User, ImagingReport
from sqlalchemy import desc
from router.auth import login_required

def get_user_role():
    """获取当前用户的角色"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    user = User.query.get(user_id)
    if user:
        return user.role
    return None

# 配置日志
logging.basicConfig(level=logging.ERROR)

# API配置
api_key = os.getenv("ALI_API_KEY", "sk-ffbe320a6b774fb5aea80ab07e62cfcb")

# 上传文件夹配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "chat_file")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 最大聊天会话数
MAX_CHAT_SESSIONS = 7


def generate_random_str(length=8):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def render_chat_page():
    """渲染聊天页面"""
    user_id = session.get('user_id')
    if user_id:
        # 获取用户的聊天会话，按更新时间降序排序
        chat_sessions = ChatSession.query.filter_by(user_id=user_id).order_by(desc(ChatSession.updated_at)).all()

        # 添加当前时间变量，确保模板中{{ now }}可用
        now = datetime.now()

        # 如果用户已有会话，使用最新的会话
        current_session = chat_sessions[0] if chat_sessions else None

        # 仅当用户没有会话时，创建新的聊天会话
        if not current_session:
            current_session = ChatSession(user_id=user_id, title="新会话")
            db.session.add(current_session)
            db.session.commit()
            # 重新获取会话列表
            chat_sessions = [current_session]

        # 获取当前用户角色
        user_role = get_user_role()

        return render_template('public/chat.html', chat_sessions=chat_sessions, now=now,
                               current_session=current_session, user_role=user_role)
    else:
        return render_template('public/login.html')


def check_fastapi_health():
    """检查 FastAPI 健康状态"""
    url = "http://localhost:8000/generate"  # 使用 generate 端点作为健康检查
    try:
        print("正在检查 FastAPI 服务状态...")
        response = requests.post(
            url,
            json={"prompt": "test", "max_length": 1},
            timeout=2
        )
        print(f"FastAPI 服务响应状态码: {response.status_code}")
        if response.status_code == 200:
            print("FastAPI 服务正常运行")
            return True
        else:
            print(f"FastAPI 服务返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"无法连接到 FastAPI 服务: {str(e)}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"连接 FastAPI 服务超时: {str(e)}")
        return False
    except Exception as e:
        print(f"检查 FastAPI 服务时发生错误: {str(e)}")
        return False


def call_fastapi_stream(prompt: str, max_length: int = 50):
    """流式调用 FastAPI 接口"""
    url = "http://localhost:8000/generate"
    try:
        response = requests.post(
            url,
            json={"prompt": prompt, "max_length": max_length},
            stream=True,
            timeout=5
        )
        if response.status_code == 200:
            def generate():
                for chunk in response.iter_lines():
                    if chunk:
                        yield chunk + b"\n\n"

            return generate()
        else:
            return iter([f"data: FastAPI Error: {response.text}\n\n".encode()])
    except requests.exceptions.ConnectionError as e:
        logging.error(f"FastAPI Connection Error: {e}")
        return iter([f"data: Error calling FastAPI: {str(e)}\n\n".encode()])
    except requests.exceptions.RequestException as e:
        logging.error(f"FastAPI Request Error: {e}")
        return iter([f"data: Error calling FastAPI: {str(e)}\n\n".encode()])


# 使用通义百炼大模型的api调用方法
def call_API_model(user_message, user_image=None):
    try:
        image_url = None
        if user_image:
            original_filename = secure_filename(user_image.filename)
            unique_filename = f"{generate_random_str()}_{original_filename}"
            image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            user_image.save(image_path)
            image_url = f"/static/chat_file/{unique_filename}"

        combined_content = []
        if user_message:
            combined_content.append({"text": user_message})
        if image_url:
            combined_content.append({"image": image_url})

        if not combined_content:
            return "没有提供有效的消息或图片"

        messages = [{
            "role": "user",
            "content": combined_content
        }]

        response = dashscope.MultiModalConversation.call(
            api_key=api_key,
            model='qwen-vl-max',
            messages=messages
        )

        choices = response.get("output", {}).get("choices", [])
        if choices and choices[0].get("message", {}).get("content", []):
            bot_response = choices[0]["message"]["content"][0].get("text", "")
        else:
            bot_response = "对不起，我无法回答这个问题。"

        if bot_response == "none":
            bot_response = "对不起，我无法回答这个问题。"

        return bot_response

    except Exception as e:
        return f"Error: {str(e)}"


def manage_chat_sessions(user_id):
    """管理用户的聊天会话数量，确保不超过最大限制"""
    # 获取所有用户会话，按更新时间排序（最旧的在前）
    user_sessions = ChatSession.query.filter_by(user_id=user_id).order_by(ChatSession.updated_at).all()

    # 如果数量超过限制，删除最早的会话（更新时间最旧的）
    if len(user_sessions) >= MAX_CHAT_SESSIONS:
        sessions_to_remove = len(user_sessions) - MAX_CHAT_SESSIONS + 1
        for i in range(sessions_to_remove):
            db.session.delete(user_sessions[i])
        db.session.commit()


def handle_chat_request():
    """处理聊天请求的统一入口"""
    try:
        data = request.form
        user_message = data.get("message", "").strip()
        user_image = request.files.get("image")
        user_id = session.get('user_id')
        session_id = data.get('session_id')
        current_action = session.get('current_action')  # 在生成器外获取current_action
        
        # 记录当前操作，帮助调试
        logging.info(f"当前请求: 用户ID={user_id}, 会话ID={session_id}, 当前动作={current_action}")
        logging.info(f"消息内容: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
        logging.info(f"是否包含图片: {bool(user_image)}")

        if not user_id:
            return jsonify({"status": "error", "message": "请先登录"}), 401

        # 获取或创建聊天会话
        chat_session = None
        if session_id:
            chat_session = ChatSession.query.filter_by(session_id=session_id, user_id=user_id).first()

        # 如果没有找到会话，创建一个新会话
        if not chat_session:
            chat_session = ChatSession(user_id=user_id, title="新会话")
            db.session.add(chat_session)
            db.session.commit()
            session_id = chat_session.session_id

            # 管理会话数量
            manage_chat_sessions(user_id)

        # 更新会话标题（使用第一条消息的前10个字符）
        if not chat_session.messages:
            title = user_message[:10] + "..." if len(user_message) > 10 else user_message
            if not title.strip():
                title = "新会话"
            chat_session.title = title

        # 更新会话的最后更新时间
        chat_session.updated_at = datetime.now()
        db.session.commit()

        # 存储用户消息
        user_content = user_message
        image_path = None
        image_url = None

        # 检查用户消息是否包含URL图片链接
        url_pattern = re.compile(r'https?://\S+\.(jpg|jpeg|png|gif|bmp|webp)', re.IGNORECASE)
        url_match = url_pattern.search(user_message)
        
        if url_match:
            # 用户输入了图片URL
            image_url = url_match.group(0)
            logging.info(f"检测到用户输入的图片URL: {image_url}")
            # 从消息中提取真正的文本部分（去除URL）
            user_content = user_message.replace(image_url, "").strip()
            if not user_content:
                user_content = "请分析这张图片"
        elif user_image:
            try:
                original_filename = secure_filename(user_image.filename)
                unique_filename = f"{generate_random_str()}_{original_filename}"
                image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                user_image.save(image_path)
                relative_path = f"/static/chat_file/{unique_filename}"
                image_url = f"http://{request.host}{relative_path}"
                user_content += f"\n[图片]{relative_path}"
            except Exception as e:
                logging.error(f"保存图片失败: {str(e)}")

        user_msg = ChatMessage(
            session_id=session_id,
            role='user',
            content=user_content,
            image_path=image_path
        )
        db.session.add(user_msg)

        # 更新会话的最后更新时间
        chat_session.updated_at = datetime.now()
        db.session.commit()

        # 提前准备好应用上下文，以便在流式响应中使用
        app = current_app._get_current_object()

        def generate():
            bot_response = ""
            report = None
            report_data = {}  # 保存完整报告数据
            yield f"data: \n\n"

            # 添加调试信息
            logging.info(f"当前会话动作: {current_action}")
            logging.info(f"是否有图片: 本地图片={bool(user_image)}, 网络图片URL={bool(image_url)}")

            if current_action == 'medical-consultation' and (user_image or image_url):
                # 使用Coze API生成报告
                try:
                    logging.info("正在调用Coze API生成报告...")
                    query = "帮我生成一个检测报告"
                    if user_content:
                        query = user_content

                    # 调用Coze API
                    conn = http.client.HTTPSConnection("api.coze.cn")
                    pic_url = image_url
                    
                    # 确保pic_url是完整的URL，如果不是，则替换为默认图像
                    if not pic_url or not pic_url.startswith("http"):
                        logging.error(f"无效的图片URL: {pic_url}")
                        yield f"data: 请提供有效的医学影像图片URL或上传图片文件。\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    logging.info(f"调用Coze API - 查询: {query}, 图片URL: {pic_url}")

                    payload = json.dumps({
                        "workflow_id": "7497248448803455027",
                        "parameters": {
                            "input": query,
                            "pic": pic_url
                        }
                    })

                    headers = {
                        'Authorization': 'Bearer pat_DJ0ZvFvXlIQ5F5NXm2TllO0wPiyDNP7cj2lxz9wp66Qv8ThUZT7FkdzcUUSGPBGA',
                        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                        'Content-Type': 'application/json',
                        'Accept': '*/*',
                        'Host': 'api.coze.cn',
                        'Connection': 'keep-alive'
                    }

                    conn.request("POST", "/v1/workflow/run", payload, headers)
                    res = conn.getresponse()
                    data = res.read()

                    response_data = json.loads(data.decode("utf-8"))
                    logging.info(f"Coze API原始响应: {response_data}")

                    if 'data' in response_data and response_data['msg'] == 'Success':
                        try:
                            inner = json.loads(response_data['data'])
                            raw = inner.get('data', '')
                            logging.info(f"解析后的原始数据: {raw}")

                            m = re.match(r'(\{.*?\})(?:.*)', raw, re.DOTALL)
                            if m:
                                nested_json = m.group(1)
                                try:
                                    report = json.loads(nested_json)
                                    logging.info(f"解析后的报告数据: {report}")
                                    # 保存完整报告数据供后续使用
                                    report_data = report.copy()
                                    bot_response = report.get('analysis', '')
                                    if not bot_response:
                                        bot_response = report.get('analisis', '').strip()
                                    if not bot_response:
                                        if 'result' in report:
                                            bot_response = report['result']
                                        elif 'content' in report:
                                            bot_response = report['content']
                                    
                                    if not bot_response:
                                        logging.warning("无法从报告JSON中找到分析结果字段")
                                    else:
                                        logging.info(f"提取的分析结果: {bot_response}")
                                        
                                except json.JSONDecodeError as e:
                                    logging.error(f"JSON解析错误: {e}")
                                    logging.error(f"尝试解析的JSON字符串: {nested_json}")
                                    bot_response = '解析报告数据失败，请重试'
                            else:
                                # 如果无法通过JSON解析，尝试直接从文本提取
                                logging.info("尝试从原始文本中提取分析结果")
                                # 首先尝试查找"分析结果："标记
                                parts = raw.split('分析结果：', 1)
                                if len(parts) > 1:
                                    # 找到标记，提取分析部分直到下一个标记（如"结论"）
                                    analysis_text = parts[1]
                                    # 查找常见的下一节标记
                                    for marker in ['结论', '总结', 'CONCLUSION', '建议']:
                                        if marker in analysis_text:
                                            analysis_text = analysis_text.split(marker, 1)[0]
                                    bot_response = analysis_text.strip()
                                    logging.info(f"通过文本分割提取的分析结果: {bot_response}")
                                # 如果仍然没有提取到有效内容，尝试其他常见标记
                                elif '诊断报告' in raw:
                                    sections = re.split(r'(诊断报告|观察发现|影像所见|检查结果)[:：]', raw)
                                    if len(sections) > 2:
                                        bot_response = sections[2].strip()
                                        logging.info(f"从诊断报告部分提取内容: {bot_response}")
                                # 实在没有找到任何有效内容，返回原始文本的一部分
                                if not bot_response:
                                    logging.error("无法从原始数据中提取分析结果")
                                    # 截取原始文本的前500个字符作为回复
                                    bot_response = '无法提取结构化分析结果，原始内容：\n' + raw[:500]

                        except Exception as e:
                            logging.error(f"解析 API 数据失败: {e}")
                            logging.error(f"原始数据: {raw}")
                            bot_response = "解析报告数据时出错，请重试"

                    else:
                        logging.error(f"API 调用失败: {response_data}")
                        bot_response = f"API 调用失败: {response_data.get('msg', '未知错误')}"

                    # 报告处理完成后，重置current_action，避免状态持续
                    try:
                        # 如果成功生成了报告，考虑保存到数据库
                        if bot_response and bot_response.strip() != '' and report_data:
                            try:
                                # 尝试保存报告数据到数据库
                                if 'ImagingReport' in globals():  # 确保ImagingReport模型可用
                                    new_report = ImagingReport(
                                        user_id=user_id,
                                        session_id=session_id,
                                        image_path=image_path,
                                        image_url=image_url,
                                        report_data=json.dumps(report_data),
                                        analysis_text=bot_response,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(new_report)
                                    db.session.commit()
                                    logging.info(f"成功保存报告数据，报告ID={new_report.report_id}")
                            except Exception as e:
                                logging.error(f"保存报告数据失败: {str(e)}")
                        
                        # 清除current_action状态
                        with app.app_context():
                            if 'current_action' in session:
                                session.pop('current_action', None)
                                logging.info("已重置current_action状态")
                    except Exception as e:
                        logging.error(f"清理会话状态失败: {str(e)}")
                                            
                    yield f"data: {bot_response}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"调用Coze API失败: {str(e)}")
                    bot_response = f"生成报告失败: {str(e)}"
                    yield f"data: {bot_response}\n\n"
                    yield "data: [DONE]\n\n"
            elif check_fastapi_health():
                try:
                    fastapi_response = call_fastapi_stream(user_message)
                    collected_response = ""
                    for chunk in fastapi_response:
                        if isinstance(chunk, bytes):
                            chunk_str = chunk.decode('utf-8')
                            if chunk_str.startswith("data: "):
                                content = chunk_str[6:].strip()
                                if content and content != "[DONE]":
                                    collected_response += content
                        yield chunk
                    bot_response = collected_response
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logging.error(f"FastAPI调用失败: {str(e)}")
                    bot_response = call_API_model(user_message, user_image)
                    yield f"data: {bot_response}\n\n"
                    yield "data: [DONE]\n\n"
            else:
                bot_response = call_API_model(user_message, user_image)
                yield f"data: {bot_response}\n\n"
                yield "data: [DONE]\n\n" 

            # 使用应用上下文保存机器人回复
            with app.app_context():
                try:
                    bot_msg = ChatMessage(session_id=session_id, role='bot', content=bot_response)
                    db.session.add(bot_msg)

                    # 更新会话的最后更新时间
                    chat_session = ChatSession.query.get(session_id)
                    if chat_session:
                        chat_session.updated_at = datetime.now()

                    db.session.commit()
                except Exception as e:
                    logging.error(f"保存机器人回复失败: {str(e)}")

        return Response(generate(), content_type="text/event-stream")

    except Exception as e:
        logging.error(f"处理聊天请求失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def get_chat_messages(session_id):
    """获取特定会话的所有消息"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "请先登录"}), 401

    # 确认会话属于当前用户
    chat_session = ChatSession.query.filter_by(session_id=session_id, user_id=user_id).first()
    if not chat_session:
        return jsonify({"status": "error", "message": "未找到聊天会话"}), 404

    # 获取会话中的所有消息，保持按时间顺序升序排序（旧消息在前，新消息在后）
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()

    # 添加调试日志
    logging.info(f"获取会话 {session_id} 的消息，共 {len(messages)} 条")

    # 格式化消息
    formatted_messages = []
    for msg in messages:
        content = msg.content
        if msg.image_path:
            content += f'<br><img src="{msg.image_path}" alt="聊天图片" style="max-width:200px; max-height:200px;" />'

        logging.info(f"消息: {msg.message_id}, 角色: {msg.role}, 内容: {content[:50]}...")

        formatted_messages.append({
            "role": msg.role,
            "content": content,
            "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify(formatted_messages)


def init_chat_routes(app):
    @app.route('/chat', methods=["GET"])
    @login_required
    def chat():
        if not session.get('logged_in'):
            return render_template('public/login.html')

        # 获取当前用户角色
        user_role = get_user_role()
        
        # 获取用户的聊天会话，按更新时间降序排序
        user_id = session.get('user_id')
        chat_sessions = ChatSession.query.filter_by(user_id=user_id).order_by(desc(ChatSession.updated_at)).all()
        
        # 添加当前时间变量
        now = datetime.now()
        
        # 如果用户已有会话，使用最新的会话
        current_session = chat_sessions[0] if chat_sessions else None
        
        # 仅当用户没有会话时，创建新的聊天会话
        if not current_session:
            current_session = ChatSession(user_id=user_id, title="新会话")
            db.session.add(current_session)
            db.session.commit()
            # 重新获取会话列表
            chat_sessions = [current_session]
            
        return render_template('public/chat.html', chat_sessions=chat_sessions, now=now,
                              current_session=current_session, user_role=user_role)

    @app.route('/chat/new', methods=["GET"])
    @login_required
    def new_chat():
        """创建新的聊天会话"""
        user_id = session.get('user_id')

        try:
            # 创建新的聊天会话
            new_session = ChatSession(user_id=user_id, title="新会话")
            db.session.add(new_session)
            db.session.commit()

            # 管理会话数量，确保不超过限制
            manage_chat_sessions(user_id)

            # 获取所有会话
            chat_sessions = ChatSession.query.filter_by(user_id=user_id).order_by(desc(ChatSession.updated_at)).all()
            now = datetime.now()
            
            # 获取当前用户角色
            user_role = get_user_role()

            # 返回渲染后的HTML
            return render_template('public/chat.html', chat_sessions=chat_sessions, now=now,
                                   current_session=new_session, user_role=user_role)
        except Exception as e:
            db.session.rollback()
            logging.error(f"创建新会话失败: {str(e)}")
            return jsonify({"status": "error", "message": f"创建新会话失败: {str(e)}"}), 500

    @app.route('/chat', methods=["POST"])
    @login_required
    def chat_response():
        return handle_chat_request()

    @app.route('/chat/<int:session_id>', methods=["GET"])
    @login_required
    def chat_history(session_id):
        return get_chat_messages(session_id)

    @app.route('/chat/session/<int:session_id>', methods=["DELETE"])
    @login_required
    def delete_chat_session(session_id):
        """删除聊天会话"""
        user_id = session.get('user_id')

        # 确认会话属于当前用户
        chat_session = ChatSession.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not chat_session:
            return jsonify({"status": "error", "message": "未找到聊天会话"}), 404

        try:
            # 删除会话（会级联删除相关消息）
            db.session.delete(chat_session)
            db.session.commit()
            return jsonify({"status": "success", "message": "会话已删除"})
        except Exception as e:
            db.session.rollback()
            logging.error(f"删除会话失败: {str(e)}")
            return jsonify({"status": "error", "message": f"删除会话失败: {str(e)}"}), 500

    @app.route('/api/chat/quick-action/<action>', methods=['POST'])
    @login_required
    def handle_quick_action(action):
        responses = {
            'medical-consultation': {
                'message': '请上传对应图片，我将帮您进行初步分析。您可以直接粘贴医学影像图片链接或上传图片文件。'
            }
        }

        logging.info(f"设置当前操作: {action}")
        session['current_action'] = action
        response = responses.get(action, {'message': '抱歉，该功能暂未实现。'})

        return jsonify(response)

    @app.route('/chat/message/<int:session_id>', methods=["DELETE"])
    @login_required
    def delete_chat_message(session_id):
        """删除聊天消息"""
        user_id = session.get('user_id')

        # 确认会话属于当前用户
        chat_session = ChatSession.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not chat_session:
            return jsonify({"status": "error", "message": "未找到聊天会话"}), 404

        # 获取要删除的消息时间
        data = request.json
        if not data or 'timestamp' not in data:
            return jsonify({"status": "error", "message": "缺少必要参数"}), 400

        timestamp = data['timestamp']

        try:

            message = ChatMessage.query.filter_by(session_id=session_id, role='user').order_by(
                ChatMessage.created_at.desc()).first()

            if message:
                bot_reply = ChatMessage.query.filter_by(session_id=session_id, role='bot').filter(
                    ChatMessage.created_at > message.created_at).first()

                db.session.delete(message)
                if bot_reply:
                    db.session.delete(bot_reply)

                db.session.commit()
                return jsonify({"status": "success", "message": "消息已删除"})
            else:
                return jsonify({"status": "error", "message": "未找到指定消息"}), 404
        except Exception as e:
            db.session.rollback()
            logging.error(f"删除消息失败: {str(e)}")
            return jsonify({"status": "error", "message": f"删除消息失败: {str(e)}"}), 500

    @app.route('/medical_analysis')
    @login_required
    def medical_analysis():
        return render_template("public/chat.html")

    @app.route("/analyse")
    @login_required
    def analyse():
        return render_template("public/chat.html")

    @app.route('/chat/open/<int:report_id>', methods=['GET'])
    @login_required
    def open_report_chat(report_id):
        return render_template("public/chat.html")

    @app.route('/api/rag_chat_html')
    def get_rag_chat_html():
        return render_template('public/rag_chat.html')
