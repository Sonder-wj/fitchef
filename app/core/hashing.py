#对密码进行加密验证

import bcrypt

#对密码进行验证
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码
    plain_password: 前端已经做过 SHA256 的密码
    hashed_password: 数据库中存储的 bcrypt 哈希
    """

    # 将两个密码都编码为 UTF-8，并使用 bcrypt.checkpw() 进行比较。如果匹配，返回 True，否则返回 False。
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

#对密码进行加密
def hash_password(password: str) -> str:
    """对密码进行哈希
    password: 前端已经做过 SHA256 的密码
    """
    #加盐 
    # → 生成一个随机"盐"，如 "$2b$12$K8xYq3Z..." 
#   每次调用都不一样，保证即使两个用户密码相同，存进数据库的密文也不同
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')