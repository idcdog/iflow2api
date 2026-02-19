"""OAuth 回调服务器 - 处理 OAuth 授权回调"""

import socket
import threading
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable, Dict, Any


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """OAuth 回调请求处理器

    回调数据通过实例引用共享的 server 对象（H-06 修复：不再使用类变量，消除并发竞态）
    """

    def log_message(self, format: str, *args: Any) -> None:
        """禁用默认日志输出"""
        pass

    def do_GET(self) -> None:
        """处理 GET 请求"""
        # 解析查询参数
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        # 提取参数
        code = query.get("code", [None])[0]
        error = query.get("error", [None])[0]
        state = query.get("state", [None])[0]

        # 将数据写入 server 实例，而非类变量
        self.server.callback_code = code      # type: ignore[attr-defined]
        self.server.callback_error = error    # type: ignore[attr-defined]
        self.server.callback_state = state    # type: ignore[attr-defined]

        # 返回响应
        if code:
            self._send_success_response()
        else:
            self._send_error_response(error or "授权失败")

    def _send_success_response(self) -> None:
        """发送成功响应"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>登录成功</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .icon {
                    font-size: 64px;
                    color: #4CAF50;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                p {
                    color: #666;
                    margin-bottom: 20px;
                }
                .hint {
                    font-size: 14px;
                    color: #999;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✓</div>
                <h1>登录成功！</h1>
                <p>您可以关闭此页面并返回应用程序。</p>
                <p class="hint">此页面将在 5 秒后自动关闭...</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 5000);
                </script>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def _send_error_response(self, error_message: str) -> None:
        """发送错误响应"""
        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>登录失败</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .icon {{
                    font-size: 64px;
                    color: #f44336;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                p {{
                    color: #666;
                    margin-bottom: 20px;
                }}
                .error {{
                    color: #f44336;
                    font-weight: bold;
                    margin-bottom: 20px;
                }}
                .hint {{
                    font-size: 14px;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✕</div>
                <h1>登录失败</h1>
                <p class="error">{error_message}</p>
                <p>请重试或联系技术支持。</p>
                <p class="hint">此页面将在 5 秒后自动关闭...</p>
                <script>
                    setTimeout(function() {{
                        window.close();
                    }}, 5000);
                </script>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))


class OAuthCallbackServer:
    """OAuth 回调服务器"""

    def __init__(self, host: str = "localhost", port: int = 11451):
        """
        初始化 OAuth 回调服务器

        Args:
            host: 监听地址
            port: 监听端口
        """
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def is_port_available(self, port: Optional[int] = None) -> bool:
        """
        检查端口是否可用

        Args:
            port: 要检查的端口，默认使用 self.port

        Returns:
            True 表示端口可用，False 表示端口被占用
        """
        check_port = port if port is not None else self.port

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, check_port))
                return True
        except OSError:
            return False

    def start(self) -> bool:
        """
        启动 OAuth 回调服务器

        Returns:
            True 表示启动成功，False 表示启动失败
        """
        if self._running:
            return True

        # 检查端口是否可用
        if not self.is_port_available():
            return False

        try:
            # 创建服务器
            self._server = HTTPServer((self.host, self.port), OAuthCallbackHandler)
            # 实例级回调数据（H-06 修复：不再使用类变量）
            self._server.callback_code = None   # type: ignore[attr-defined]
            self._server.callback_error = None  # type: ignore[attr-defined]
            self._server.callback_state = None  # type: ignore[attr-defined]

            # 启动服务器线程
            self._thread = threading.Thread(target=self._run_server, daemon=True)
            self._thread.start()

            self._running = True
            return True
        except Exception:
            return False

    def _run_server(self) -> None:
        """运行服务器（在独立线程中）"""
        if self._server:
            self._server.serve_forever()

    def stop(self) -> None:
        """停止 OAuth 回调服务器"""
        if self._server and self._running:
            self._server.shutdown()
            self._server.server_close()
            self._running = False

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        self._server = None

    def wait_for_callback(
        self,
        timeout: int = 60,
        callback: Optional[Callable[[Optional[str], Optional[str]], None]] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        等待 OAuth 回调

        Args:
            timeout: 超时时间（秒）
            callback: 回调函数，接收 (code, error) 参数

        Returns:
            (auth_code, error, state) 三元组，state 供调用方做 CSRF 校验
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not self._server:
                return None, "server_stopped", None
            code = self._server.callback_code    # type: ignore[attr-defined]
            error = self._server.callback_error  # type: ignore[attr-defined]
            state = self._server.callback_state  # type: ignore[attr-defined]
            if code is not None or error is not None:
                if callback:
                    callback(code, error)
                return code, error, state
            time.sleep(0.1)

        # 超时
        if callback:
            callback(None, "timeout")

        return None, "timeout", None

    def get_callback_url(self) -> str:
        """
        获取回调 URL

        Returns:
            回调 URL
        """
        return f"http://{self.host}:{self.port}/oauth2callback"

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()


def find_available_port(
    start_port: int = 11451, max_attempts: int = 10
) -> Optional[int]:
    """
    查找可用端口

    Args:
        start_port: 起始端口
        max_attempts: 最大尝试次数

    Returns:
        可用端口号，如果找不到则返回 None
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue

    return None
