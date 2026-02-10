"""AES加密/解密工具模块

提供AES-256-CBC模式的加密和解密功能，用于保护本地授权信息。
"""

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad


def aes_encrypt(data: bytes, key: bytes) -> bytes:
    """AES-256-CBC加密

    Args:
        data: 待加密的字节数据
        key: AES密钥（16/24/32字节）

    Returns:
        bytes: 加密后的数据

    Raises:
        ValueError: 如果密钥长度不是16/24/32字节
    """
    if len(key) not in [16, 24, 32]:
        raise ValueError("AES密钥必须是16、24或32字节")

    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    return cipher.encrypt(pad(data, AES.block_size))


def aes_decrypt(encrypted_data: bytes, key: bytes) -> bytes:
    """AES-256-CBC解密

    Args:
        encrypted_data: 加密的字节数据
        key: AES密钥（16/24/32字节，必须与加密时相同）

    Returns:
        bytes: 解密后的原始数据

    Raises:
        ValueError: 如果密钥长度不是16/24/32字节
        BadPaddingException: 如果解密失败或数据被篡改
    """
    if len(key) not in [16, 24, 32]:
        raise ValueError("AES密钥必须是16、24或32字节")

    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    return unpad(cipher.decrypt(encrypted_data), AES.block_size)
