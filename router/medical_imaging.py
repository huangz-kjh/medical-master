import os
import sys
import logging
import time
import requests
from flask import render_template, Response, redirect, request, jsonify, stream_with_context
import socket
from urllib.parse import urljoin, urlparse

# 导入状态检查函数和配置参数
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from vue_builder import check_app_health, get_app_url, CONFIG
    # 使用统一配置参数
    VOXLOGICA_SERVER_URL = CONFIG["SERVER_URL"]
except ImportError:
    # 如果vue_builder被删除，使用默认设置
    CONFIG = {
        "SERVER_URL": "http://118.195.132.5/",
        "SERVER_PORT": 80,
        "APP_DIR_NAME": "predict-master",
        "PM2_SCRIPT_PATH": "server.js",
        "APP_NAME": "medical-imaging"
    }
    VOXLOGICA_SERVER_URL = "http://118.195.132.5/"

    def check_app_health():
        """检查应用健康状态"""
        return False

    def get_app_url(path):
        """获取应用URL"""
        return urljoin(VOXLOGICA_SERVER_URL, path)

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("medical_imaging")



def render_not_ready_page():
    """渲染Vue服务器未启动页面

    Returns:
        Flask响应对象
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>医学影像系统 - 服务未启动</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }
            .container {
                text-align: center;
                padding: 2rem;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                max-width: 600px;
                width: 90%;
            }
            h1 {
                color: #e74c3c;
                margin-bottom: 1rem;
            }
            p {
                color: #333;
                margin-bottom: 1.5rem;
                line-height: 1.6;
            }
            .code-block {
                background-color: #f1f1f1;
                padding: 15px;
                border-radius: 4px;
                font-family: monospace;
                text-align: left;
                margin: 15px 0;
                white-space: pre-wrap;
            }
            .button {
                display: inline-block;
                padding: 10px 20px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
            }
            .button:hover {
                background-color: #2980b9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Vue开发服务器未运行</h1>
            <p>
                要使用医学影像分析系统，您需要在终端中手动启动Vue开发服务器。
                请在终端中执行以下命令：
            </p>

            <div class="code-block">
                npm run dev
            </div>

            <p>
                启动成功后，您将看到类似以下输出：
            </p>

            <div class="code-block">
                VITE v5.4.11  ready in 2297 ms

                ➜  Local:   http://localhost:5173/
                ➜  Network: use --host to expose
            </div>

            <p>
                服务启动后，请刷新此页面
            </p>

            <a href="javascript:window.location.reload()" class="button">刷新页面</a>
        </div>
    </body>
    </html>
    """
    return Response(html_content, mimetype='text/html')


def render_external_iframe_page():
    """渲染嵌入外部服务器iframe的页面

    Returns:
        Flask响应对象
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VoxLogicA 3D医学影像分析</title>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                height: 100%;
                overflow: hidden;
                font-family: "Microsoft YaHei", Arial, sans-serif;
                background-color: #f7f9fc;
            }}
            .iframe-container {{
                width: 100%;
                height: 100vh;
                position: relative;
            }}
            #voxlogica-app {{
                width: 100%;
                height: 100%;
                border: none;
                position: absolute;
                top: 0;
                left: 0;
            }}
        </style>
    </head>
    <body>
        <div class="iframe-container">
            <iframe id="voxlogica-app" src="{VOXLOGICA_SERVER_URL}/" allow="fullscreen"></iframe>
        </div>
    </body>
    </html>
    """
    return Response(html_content, mimetype='text/html')


def render_iframe_page(override_server_url=None):
    """渲染医学影像分析系统页面，包含自动检测服务可用性功能

    Args:
        override_server_url: 可选的服务器URL覆盖值

    Returns:
        Flask响应对象
    """
    server_url = override_server_url or CONFIG["SERVER_URL"]
    app_dir = CONFIG["APP_DIR_NAME"]
    script_path = CONFIG["PM2_SCRIPT_PATH"]
    app_name = CONFIG["APP_NAME"]

    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>医学影像分析系统</title>
        <style>
            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                overflow: hidden;
                font-family: "Microsoft YaHei", Arial, sans-serif;
                background-color: #f5f5f5;
            }
            .iframe-container {
                width: 100%;
                height: 100vh;
                position: relative;
                display: none;
            }
            #app-iframe {
                width: 100%;
                height: 100%;
                border: none;
            }
            .loading-container {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f5f5f5;
            }
            .spinner {
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }
            .error-container {
                display: none;
                padding: 20px;
                max-width: 650px;
                margin: 20px auto;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            .error-title {
                color: #e74c3c;
                font-size: 24px;
                margin-bottom: 15px;
            }
            .error-message {
                margin-bottom: 20px;
                line-height: 1.6;
            }
            .code-block {
                background-color: #f1f1f1;
                padding: 15px;
                border-radius: 4px;
                font-family: monospace;
                text-align: left;
                margin: 15px 0;
                white-space: pre-wrap;
            }
            .button {
                display: inline-block;
                padding: 10px 20px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
                cursor: pointer;
            }
            .button:hover {
                background-color: #2980b9;
            }
            .note {
                background-color: #fff9e6;
                border-left: 4px solid #f1c40f;
                padding: 10px 15px;
                margin: 15px 0;
                text-align: left;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <!-- 加载中显示 -->
        <div id="loading" class="loading-container">
            <div class="spinner"></div>
            <p>正在连接到服务器...</p>
        </div>

        <!-- iframe容器 -->
        <div id="iframe-container" class="iframe-container">
            <iframe id="app-iframe" src=""" + f'"{server_url}"' + """ allow="fullscreen"></iframe>
        </div>

        <!-- 错误信息显示 -->
        <div id="error-container" class="error-container">
            <h2 class="error-title">无法连接到服务器</h2>
            <p class="error-message">
                系统无法连接到医学影像分析服务器，可能是服务器未启动或网络问题。
                请按照以下步骤启动服务器：
            </p>

            <div class="code-block">
# 1. 检查PM2是否已安装
npm list -g pm2
# 如果未安装，执行: npm install -g pm2

# 2. 启动应用服务器
cd """ + f"{app_dir}" + """
npm run build
pm2 start """ + f"{script_path}" + """ --name """ + f"{app_name}" + """</div>

            <div class="note">
                <p>成功启动后，服务将运行在: <strong>""" + f"{server_url}" + """</strong></p>
                <p>您可以通过命令 <code>pm2 logs """ + f"{app_name}" + """</code> 查看应用日志</p>
            </div>

            <a href="javascript:window.location.reload()" class="button">刷新页面</a>
        </div>

        <script>
            // 获取页面元素
            const loadingElement = document.getElementById('loading');
            const iframeContainer = document.getElementById('iframe-container');
            const errorContainer = document.getElementById('error-container');
            const appIframe = document.getElementById('app-iframe');

            // 设置超时时间（毫秒）
            const TIMEOUT = 15000;
            let isLoaded = false;

            // 检查服务器状态
            function checkServerStatus() {
                fetch('/medical_imaging/api/check-vue-server')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'ok') {
                            // 服务正常
                            showIframe();
                        } else {
                            // 服务不可用
                            showError();
                        }
                    })
                    .catch(error => {
                        // 请求出错
                        console.error('检查服务器状态失败:', error);
                        showError();
                    });
            }

            // 获取当前域名并尝试使用同源URL
            function tryLocalServerUrl() {
                // 获取当前协议和域名
                const protocol = window.location.protocol;
                const host = window.location.host;

                // 构建同源URL
                const sameOriginUrl = `${protocol}//${host}`;
                console.log("尝试使用同源URL: " + sameOriginUrl);

                // 修改iframe的src属性
                appIframe.src = sameOriginUrl;

                // 在500ms后检查是否加载成功
                setTimeout(function() {
                    if (!isLoaded) {
                        // 如果仍然未加载成功，回退到原始URL
                        appIframe.src = """ + f'"{server_url}"' + """;
                    }
                }, 500);
            }

            // 显示iframe
            function showIframe() {
                loadingElement.style.display = 'none';
                errorContainer.style.display = 'none';
                iframeContainer.style.display = 'block';
                isLoaded = true;
            }

            // 显示错误信息
            function showError() {
                loadingElement.style.display = 'none';
                iframeContainer.style.display = 'none';
                errorContainer.style.display = 'block';
            }

            // iframe加载成功
            appIframe.onload = function() {
                try {
                    // 尝试访问iframe内容（可能会因跨域失败，但不影响显示）
                    console.log("iframe加载完成");
                    showIframe();
                } catch (e) {
                    // 继续显示iframe，但进行额外检查
                    showIframe();
                    console.warn("无法检查iframe内容:", e);
                }
            };

            // iframe加载失败
            appIframe.onerror = function() {
                console.log("iframe加载失败，尝试同源URL");
                tryLocalServerUrl();
            };

            // 设置超时处理
            setTimeout(function() {
                if (!isLoaded) {
                    console.log("加载超时，尝试同源URL");
                    tryLocalServerUrl();
                }
            }, TIMEOUT);
        </script>
    </body>
    </html>
    """

    return Response(html_content, mimetype='text/html')


def check_server_accessibility(url="http://118.195.132.5/", timeout=5):
    """检查服务器是否可访问

    Args:
        url: 要检查的服务器URL
        timeout: 超时时间(秒)

    Returns:
        bool: 服务器是否可访问
    """
    # 确保URL包含协议
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url

    try:
        # 方法1：使用socket连接测试
        # 移除URL的协议部分，获取主机名
        if "://" in url:
            hostname = url.split('://')[1].split('/')[0]
        else:
            hostname = url.split('/')[0]

        # 如果主机名包含端口，分离端口
        if ':' in hostname:
            hostname, port_str = hostname.split(':')
            port = int(port_str)
        else:
            # 根据协议确定默认端口
            if url.startswith('https://'):
                port = 443
            else:
                port = 80

        # 创建socket连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        socket_result = sock.connect_ex((hostname, port))
        sock.close()

        if socket_result == 0:
            logger.info(f"Socket连接到 {hostname}:{port} 成功")

            # 方法2：尝试HTTP请求以确认服务可用
            try:
                http_response = requests.get(url, timeout=timeout)
                if http_response.status_code < 400:
                    logger.info(f"HTTP请求到 {url} 成功，状态码: {http_response.status_code}")
                    return True
                else:
                    logger.warning(f"HTTP请求到 {url} 返回错误状态码: {http_response.status_code}")
                    # 即使HTTP返回错误，只要能连接上，我们也认为服务器可访问
                    return True
            except requests.exceptions.RequestException as e:
                logger.warning(f"HTTP请求到 {url} 失败: {str(e)}")
                # 即使HTTP请求失败，只要socket连接成功，我们也认为服务器可访问
                return True
        else:
            logger.warning(f"Socket连接到 {hostname}:{port} 失败，错误代码: {socket_result}")
            return False

    except Exception as e:
        logger.error(f"检查服务器访问性时出错: {str(e)}")
        return False


def render_simplified_iframe_page(server_url="http://118.195.132.5/"):
    """渲染简化版iframe页面，首先检查服务器可访问性

    Args:
        server_url: 服务器URL

    Returns:
        Flask响应对象
    """
    # 检查服务器是否可访问
    is_accessible = check_server_accessibility(server_url)

    # 获取当前请求的协议和主机名，用于构建代理URL
    request_scheme = request.headers.get('X-Forwarded-Proto', 'http')
    if request.is_secure:
        request_scheme = 'https'
    elif request.url.startswith('https://'):
        request_scheme = 'https'

    # 构建基于当前协议的URL
    current_host = f"{request_scheme}://{request.host}"
    proxy_base_url = f"{current_host}/medical_imaging/proxy"

    if is_accessible:
        # 服务器可访问，显示iframe页面但添加客户端错误处理
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoxLogicA 3D医学影像分析</title>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    overflow: hidden;
                    font-family: "Microsoft YaHei", Arial, sans-serif;
                    background-color: #f7f9fc;
                }}
                .iframe-container {{
                    width: 100%;
                    height: 100vh;
                    position: relative;
                }}
                #voxlogica-app {{
                    width: 100%;
                    height: 100%;
                    border: none;
                    position: absolute;
                    top: 0;
                    left: 0;
                }}
                .loading-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background-color: #f5f5f5;
                }}
                .spinner {{
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 20px;
                }}
                .error-container {{
                    display: none;
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    max-width: 600px;
                    width: 90%;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }}
                .cloud-icon {{
                    font-size: 72px;
                    color: #95a5a6;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #e74c3c;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #333;
                    margin-bottom: 1.5rem;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #3498db;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                .button:hover {{
                    background-color: #2980b9;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <!-- 加载中显示 -->
            <div id="loading" class="loading-container">
                <div class="spinner"></div>
                <p>正在连接到服务器...</p>
            </div>

            <!-- iframe容器 -->
            <div id="iframe-container" class="iframe-container" style="display: none;">
                <iframe id="voxlogica-app" src="about:blank" allow="fullscreen"></iframe>
            </div>

            <!-- 错误信息显示 -->
            <div id="error-container" class="error-container">
                <div class="cloud-icon">
                    ☁️
                </div>
                <h1>无法连接到服务器</h1>
                <p>系统无法连接到医学影像分析服务器 (43.134.119.222)。</p>
                <p>请检查您的网络连接或联系系统管理员。</p>
                <a href="javascript:window.location.reload()" class="button">刷新页面</a>
            </div>

            <script>
                // 当前页面的协议
                const currentProtocol = window.location.protocol;

                // 调整服务器URL以匹配当前协议
                const serverProtocol = "{server_url}".startsWith("https") ? "https:" : "http:";
                const protocolMatchedServerUrl = "{server_url}".replace(/^https?:/, currentProtocol);

                // 调整代理URL以匹配当前协议
                const protocolMatchedProxyUrl = "{proxy_base_url}".replace(/^https?:/, currentProtocol);

                // 获取页面元素
                const loadingElement = document.getElementById('loading');
                const iframeContainer = document.getElementById('iframe-container');
                const errorContainer = document.getElementById('error-container');
                const appIframe = document.getElementById('voxlogica-app');

                // 设置超时时间（毫秒）
                const TIMEOUT = 10000;
                let isLoaded = false;
                let connectionTimer = null;

                // 显示iframe
                function showIframe() {{
                    loadingElement.style.display = 'none';
                    errorContainer.style.display = 'none';
                    iframeContainer.style.display = 'block';
                    isLoaded = true;

                    if (connectionTimer) {{
                        clearTimeout(connectionTimer);
                    }}
                }}

                // 显示错误信息
                function showError() {{
                    loadingElement.style.display = 'none';
                    iframeContainer.style.display = 'none';
                    errorContainer.style.display = 'block';

                    if (connectionTimer) {{
                        clearTimeout(connectionTimer);
                    }}
                }}

                // 使用代理URL进行连接
                function loadWithProxy() {{
                    console.log("使用代理URL加载内容");
                    // 使用代理URL (自动匹配当前协议)
                    appIframe.src = protocolMatchedProxyUrl + "/";
                }}

                // 尝试直接连接服务器
                function tryDirectConnection() {{
                    // 只有当协议匹配时才尝试直接连接
                    if (currentProtocol === "https:" && !protocolMatchedServerUrl.startsWith("https")) {{
                        console.log("当前为HTTPS页面，无法直接加载HTTP资源，直接使用代理");
                        loadWithProxy();
                        return;
                    }}

                    fetch(protocolMatchedServerUrl + '/', {{
                        mode: 'no-cors',
                        method: 'HEAD'
                    }})
                    .then(() => {{
                        // 直接连接成功，加载iframe
                        console.log("直接连接服务器成功，加载iframe");
                        appIframe.src = protocolMatchedServerUrl + '/';
                    }})
                    .catch(error => {{
                        // 直接连接失败，尝试通过代理加载
                        console.error("直接连接服务器失败，尝试代理:", error);
                        loadWithProxy();
                    }});
                }}

                // iframe加载成功
                appIframe.onload = function() {{
                    // 检查是否是空白页面
                    if (appIframe.src === 'about:blank') {{
                        return;
                    }}

                    console.log("iframe加载完成");
                    showIframe();
                }};

                // iframe加载失败
                appIframe.onerror = function(error) {{
                    console.error("iframe加载失败:", error);

                    // 如果直接连接失败，尝试使用代理
                    if (appIframe.src.includes("{server_url}")) {{
                        console.log("直接连接失败，尝试使用代理");
                        loadWithProxy();
                    }} else if (appIframe.src.includes("{proxy_base_url}")) {{
                        // 如果代理也失败，显示错误
                        console.log("代理连接也失败，显示错误");
                        showError();
                    }} else {{
                        showError();
                    }}
                }};

                // 设置超时处理
                connectionTimer = setTimeout(function() {{
                    if (!isLoaded) {{
                        console.error("加载超时，尝试代理");
                        loadWithProxy();

                        // 再设置一个代理的超时
                        setTimeout(function() {{
                            if (!isLoaded) {{
                                console.error("代理加载也超时");
                                showError();
                            }}
                        }}, 5000);
                    }}
                }}, TIMEOUT);

                // 先尝试直接连接
                // tryDirectConnection();
                loadWithProxy();
            </script>
        </body>
        </html>
        """
    else:
        # 尝试通过代理访问
        # 即使服务器端检测失败，也尝试在客户端通过代理访问
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoxLogicA 3D医学影像分析</title>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    overflow: hidden;
                    font-family: "Microsoft YaHei", Arial, sans-serif;
                    background-color: #f7f9fc;
                }}
                .iframe-container {{
                    width: 100%;
                    height: 100vh;
                    position: relative;
                    display: none;
                }}
                #voxlogica-app {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                .loading-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background-color: #f5f5f5;
                }}
                .spinner {{
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 20px;
                }}
                .error-container {{
                    display: none;
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    max-width: 600px;
                    width: 90%;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }}
                .cloud-icon {{
                    font-size: 72px;
                    color: #95a5a6;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #e74c3c;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #333;
                    margin-bottom: 1.5rem;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #3498db;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                .button:hover {{
                    background-color: #2980b9;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <!-- 加载中显示 -->
            <div id="loading" class="loading-container">
                <div class="spinner"></div>
                <p>尝试通过代理连接服务器...</p>
            </div>

            <!-- iframe容器 -->
            <div id="iframe-container" class="iframe-container">
                <iframe id="voxlogica-app" src="about:blank" allow="fullscreen"></iframe>
            </div>

            <!-- 错误信息显示 -->
            <div id="error-container" class="error-container">
                <div class="cloud-icon">
                    ☁️
                </div>
                <h1>无法连接到服务器</h1>
                <p>系统无法连接到医学影像分析服务器。</p>
                <p>请检查您的网络连接或联系系统管理员。</p>
                <a href="javascript:window.location.reload()" class="button">刷新页面</a>
            </div>

            <script>
                // 当前页面的协议
                const currentProtocol = window.location.protocol;

                // 调整代理URL以匹配当前协议
                const protocolMatchedProxyUrl = "{proxy_base_url}".replace(/^https?:/, currentProtocol);

                // 获取页面元素
                const loadingElement = document.getElementById('loading');
                const iframeContainer = document.getElementById('iframe-container');
                const errorContainer = document.getElementById('error-container');
                const appIframe = document.getElementById('voxlogica-app');

                // 设置超时时间（毫秒）
                const TIMEOUT = 15000;
                let isLoaded = false;

                // 显示iframe
                function showIframe() {{
                    loadingElement.style.display = 'none';
                    errorContainer.style.display = 'none';
                    iframeContainer.style.display = 'block';
                    isLoaded = true;
                }}

                // 显示错误信息
                function showError() {{
                    loadingElement.style.display = 'none';
                    iframeContainer.style.display = 'none';
                    errorContainer.style.display = 'block';
                }}

                // 使用代理加载
                function loadWithProxy() {{
                    console.log("尝试使用代理");
                    appIframe.src = protocolMatchedProxyUrl + "/";
                }}

                // iframe加载成功
                appIframe.onload = function() {{
                    // 检查是否是空白页面
                    if (appIframe.src === 'about:blank') {{
                        return;
                    }}

                    console.log("iframe加载完成");
                    showIframe();
                }};

                // iframe加载失败
                appIframe.onerror = function(error) {{
                    console.error("iframe加载失败:", error);
                    showError();
                }};

                // 设置超时处理
                setTimeout(function() {{
                    if (!isLoaded) {{
                        console.error("加载超时");
                        showError();
                    }}
                }}, TIMEOUT);

                // 开始尝试使用代理加载
                loadWithProxy();
            </script>
        </body>
        </html>
        """

    return Response(html_content, mimetype='text/html')


def init_medical_imaging_routes(app):
    """初始化医疗影像相关路由

    Args:
        app: Flask应用实例
    """
    # 获取当前工作目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    vue_dir = os.path.join(parent_dir, 'predict-master')

    logger.info(f"医疗影像模块初始化，Vue目录: {vue_dir}")

    @app.route('/medical_imaging')
    def medical_imaging():
        """医疗影像菜单入口，显示iframe页面"""
        # 从URL参数中获取服务器地址，默认使用43.134.119.222
        server_url = request.args.get('server_url', "http://118.195.132.5/")
        return render_simplified_iframe_page(server_url)

    @app.route('/3d')
    def three_d():
        """展示3D影像分析页面，直接加载外部VoxLogicA服务"""
        # 从URL参数中获取服务器地址，默认使用43.134.119.222
        server_url = request.args.get('server_url', "http://118.195.132.5/")
        return render_simplified_iframe_page(server_url)

    # 添加代理功能 - 核心解决方案
    @app.route('/medical_imaging/proxy/', defaults={'path': ''})
    @app.route('/medical_imaging/proxy/<path:path>')
    def proxy_to_medical_server(path):
        """代理所有请求到医学影像服务器

        这个函数处理所有发送到/medical_imaging/proxy/的请求，
        将它们转发到43.134.119.222，并将响应返回给客户端。
        这样可以解决跨域问题和内网穿透环境下无法直接连接外部服务器的问题。
        """
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        target_url = urljoin(VOXLOGICA_SERVER_URL, path)

        # 添加查询参数
        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"代理请求: {request.method} {target_url}")

        # 处理预检请求
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Content-Security-Policy'] = "frame-ancestors *;"
            return response

        try:
            # 创建请求
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=10
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=1024)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 设置内容安全策略，允许iframe加载
            if 'Content-Security-Policy' in response.headers:
                del response.headers['Content-Security-Policy']
            response.headers['Content-Security-Policy'] = "frame-ancestors *;"

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"代理请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500

    @app.route('/medical_imaging/api/check-vue-server')
    def check_vue_server():
        """API端点：检查Vue服务器状态"""
        if check_app_health():
            return jsonify({
                "status": "ok",
                "message": "Vue服务器运行正常"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Vue开发服务器未运行，请先手动启动"
            })

    # 添加配置端点
    @app.route('/medical_imaging/config', methods=['GET', 'POST'])
    def configure_server():
        """配置服务器地址

        GET: 返回当前配置
        POST: 更新配置
        """
        if request.method == 'POST':
            server_url = request.form.get('server_url')
            if server_url:
                # 设置环境变量
                os.environ['VOXLOGICA_SERVER_URL'] = server_url
                # 返回成功信息
                return jsonify({
                    "success": True,
                    "message": f"服务器地址已更新为: {server_url}",
                    "server_url": server_url
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "未提供服务器地址"
                }), 400
        else:
            # 返回当前配置
            return jsonify({
                "server_url": CONFIG["SERVER_URL"],
                "server_port": CONFIG["SERVER_PORT"]
            })

    # 为常见API路径添加直接代理
    # 这些路由处理应用内部的API请求
    @app.route('/datasets', methods=['GET', 'POST', 'OPTIONS'])
    def proxy_datasets():
        """代理数据集API"""
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        target_url = urljoin(VOXLOGICA_SERVER_URL, "datasets")

        # 处理预检请求
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"直接代理数据集请求: {request.method} {target_url}")

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=20
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"代理数据集请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500

    @app.route('/scripts', methods=['GET', 'POST', 'OPTIONS'])
    def proxy_scripts():
        """代理脚本API"""
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        target_url = urljoin(VOXLOGICA_SERVER_URL, "scripts")

        # 处理预检请求
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"直接代理脚本请求: {request.method} {target_url}")

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=20
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"代理脚本请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500

    # 处理工作区API的代理
    @app.route('/workspaces', methods=['GET', 'POST', 'OPTIONS'])
    def proxy_workspaces():
        """代理工作区API"""
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        target_url = urljoin(VOXLOGICA_SERVER_URL, "workspaces")

        # 处理预检请求
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"直接代理工作区请求: {request.method} {target_url}")

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=20
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"代理工作区请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500

    # 处理特定工作区的请求
    @app.route('/workspaces/<workspace_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
    @app.route('/workspaces/<workspace_id>/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    def proxy_workspace_detail(workspace_id, subpath=None):
        """代理特定工作区的API请求"""
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        # 处理预检请求
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        path = f"workspaces/{workspace_id}"
        if subpath:
            path = f"workspaces/{workspace_id}/{subpath}"

        target_url = urljoin(VOXLOGICA_SERVER_URL, path)

        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"直接代理工作区详情请求: {request.method} {target_url}")

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=20
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"代理工作区详情请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500

    # 通用反向代理，处理任何未明确定义的路径
    @app.route('/<path:undefined_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    def proxy_anything(undefined_path):
        """通用代理，处理所有未明确定义的路径"""
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            logger.warning(f"WebSocket upgrade request to {request.path} blocked.")
            return jsonify({"error": "WebSocket proxy not supported"}), 501

        # 增加过滤条件，跳过不需要代理的请求 (如 .well-known, favicon.ico)
        if undefined_path.startswith('.') or undefined_path == 'favicon.ico':
            return jsonify({"status": "ignored", "reason": "internal or browser-specific request"}), 404

        # 如果路径已经有明确的处理函数，则不会进入这个函数
        if undefined_path.startswith(('medical_imaging', 'api', 'static', '3d')):
            # 这些路径有自己的处理函数，不应该在这里处理
            return jsonify({
                "error": "路径未找到",
                "path": undefined_path
            }), 404

        target_url = urljoin(VOXLOGICA_SERVER_URL, undefined_path)

        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"

        logger.info(f"通用代理请求: {request.method} {target_url}")

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={key: value for key, value in request.headers if key.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=20
            )

            # 创建响应
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )

            # 复制响应头
            for key, value in resp.headers.items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 'x-frame-options'):
                    response.headers[key] = value

            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'

            return response

        except Exception as e:
            logger.error(f"通用代理请求失败: {str(e)}")
            return jsonify({
                "error": "代理请求失败",
                "message": str(e)
            }), 500
