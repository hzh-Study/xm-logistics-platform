"""安全工具：口令哈希、opaque token、摘要与 CSRF token。"""

import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """用 PBKDF2-HMAC-SHA256 派生口令哈希，返回持久化的编码串。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """校验口令与持久化哈希是否匹配。"""
    algorithm, salt_hex, digest_hex = encoded.split("$")
    if algorithm != "pbkdf2":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_token() -> str:
    """生成 opaque 会话 token。"""
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    """返回字符串的 SHA-256 十六进制摘要。"""
    return hashlib.sha256(value.encode()).hexdigest()


def new_csrf_token() -> str:
    """生成 CSRF token。"""
    return secrets.token_urlsafe(32)
