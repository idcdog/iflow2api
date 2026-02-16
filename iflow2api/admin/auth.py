"""Web 管理界面认证模块"""

import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class AdminUser(BaseModel):
    """管理员用户"""
    username: str
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """Token 数据"""
    username: str
    exp: datetime
    iat: datetime


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self._users: dict[str, AdminUser] = {}
        self._active_tokens: dict[str, TokenData] = {}
        self._config_path = Path.home() / ".iflow2api" / "admin_users.json"
        self._jwt_secret = secrets.token_hex(32)
        self._load_users()

    def _load_users(self) -> None:
        """加载用户数据"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for username, user_data in data.get("users", {}).items():
                        self._users[username] = AdminUser(
                            username=username,
                            password_hash=user_data["password_hash"],
                            created_at=datetime.fromisoformat(user_data["created_at"]),
                            last_login=datetime.fromisoformat(user_data["last_login"]) 
                            if user_data.get("last_login") else None,
                        )
                    # 加载 JWT secret 以保持 token 持久有效
                    if "jwt_secret" in data:
                        self._jwt_secret = data["jwt_secret"]
            except Exception:
                pass

    def _save_users(self) -> None:
        """保存用户数据"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "users": {
                username: {
                    "password_hash": user.password_hash,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                }
                for username, user in self._users.items()
            },
            "jwt_secret": self._jwt_secret,
        }
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _hash_password(password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, password: str) -> bool:
        """创建用户"""
        if username in self._users:
            return False
        
        user = AdminUser(
            username=username,
            password_hash=self._hash_password(password),
            created_at=datetime.now(),
        )
        self._users[username] = user
        self._save_users()
        return True

    def delete_user(self, username: str) -> bool:
        """删除用户"""
        if username not in self._users:
            return False
        
        del self._users[username]
        # 清除该用户的所有 token
        tokens_to_remove = [
            token for token, data in self._active_tokens.items()
            if data.username == username
        ]
        for token in tokens_to_remove:
            del self._active_tokens[token]
        
        self._save_users()
        return True

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        if username not in self._users:
            return False
        
        user = self._users[username]
        if user.password_hash != self._hash_password(old_password):
            return False
        
        user.password_hash = self._hash_password(new_password)
        # 清除该用户的所有 token，强制重新登录
        tokens_to_remove = [
            token for token, data in self._active_tokens.items()
            if data.username == username
        ]
        for token in tokens_to_remove:
            del self._active_tokens[token]
        
        self._save_users()
        return True

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """验证用户并返回 token"""
        if username not in self._users:
            return None
        
        user = self._users[username]
        if user.password_hash != self._hash_password(password):
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        self._save_users()
        
        # 创建 token
        token = create_access_token(username, self._jwt_secret)
        self._active_tokens[token] = TokenData(
            username=username,
            exp=datetime.now() + timedelta(hours=24),
            iat=datetime.now(),
        )
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """验证 token 并返回用户名"""
        if token not in self._active_tokens:
            return None
        
        token_data = self._active_tokens[token]
        if datetime.now() > token_data.exp:
            del self._active_tokens[token]
            return None
        
        return token_data.username

    def logout(self, token: str) -> bool:
        """登出"""
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        return False

    def get_users(self) -> list[dict]:
        """获取所有用户列表"""
        return [
            {
                "username": user.username,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            for user in self._users.values()
        ]

    def has_users(self) -> bool:
        """检查是否有用户"""
        return len(self._users) > 0


def create_access_token(username: str, secret: str) -> str:
    """创建访问令牌"""
    # 简单的 token 生成：用户名 + 时间戳 + 随机数 + 签名
    timestamp = str(int(time.time() * 1000))
    random_part = secrets.token_hex(16)
    data = f"{username}:{timestamp}:{random_part}"
    signature = hashlib.sha256(f"{data}:{secret}".encode()).hexdigest()[:32]
    return f"{data}:{signature}"


def verify_token(token: str, secret: str) -> Optional[str]:
    """验证令牌并返回用户名"""
    try:
        parts = token.split(":")
        if len(parts) != 4:
            return None
        
        username, timestamp, random_part, signature = parts
        data = f"{username}:{timestamp}:{random_part}"
        expected_signature = hashlib.sha256(f"{data}:{secret}".encode()).hexdigest()[:32]
        
        if signature != expected_signature:
            return None
        
        # 检查时间戳（可选，token 有效期由 AuthManager 管理）
        return username
    except Exception:
        return None


# 全局认证管理器实例
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """获取全局认证管理器实例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
