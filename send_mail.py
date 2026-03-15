"""
扫雷程序邮件通知模块。
通过环境变量或本地 .env 文件配置 SMTP，未配置时不会发送邮件也不会报错。
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate


def _is_configured() -> bool:
    """检查是否已配置邮件（至少需要发件人、密码和收件人）。"""
    return bool(
        os.environ.get("SMTP_USER")
        and os.environ.get("SMTP_PASSWORD")
        and os.environ.get("NOTIFY_EMAIL")
    )


def _get_smtp_config():
    """从环境变量读取 SMTP 配置。"""
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.qq.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "to_email": os.environ.get("NOTIFY_EMAIL"),
    }


def send_email(subject: str, body: str, body_html: str | None = None) -> bool:
    """
    发送一封邮件到 NOTIFY_EMAIL。
    使用环境变量：SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL。
    若未配置则直接返回 False，不抛错。
    """
    if not _is_configured():
        return False
    cfg = _get_smtp_config()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["user"]
    msg["To"] = cfg["to_email"]
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], cfg["to_email"], msg.as_string())
        return True
    except Exception:
        return False


def notify_solve_error(round_index: int, elapsed_seconds: float) -> bool:
    """
    在某一关求解失败时发送通知邮件。
    round_index: 当前是第几关（从 0 开始）
    elapsed_seconds: 本关耗时（秒）
    """
    subject = "[扫雷] 求解失败通知"
    body = (
        f"扫雷自动求解在第 {round_index} 关失败。\n"
        f"本关耗时：{elapsed_seconds:.2f} 秒。\n"
        "请检查程序或棋盘状态。"
    )
    return send_email(subject, body)


def notify_solve_complete(total_rounds: int) -> bool:
    """
    全部关卡求解结束时发送通知邮件。
    total_rounds: 共完成的关卡数（即 rounds 参数）。
    """
    subject = "[扫雷] 全部关卡完成"
    body = f"扫雷自动求解已跑完所有 {total_rounds} 关。"
    return send_email(subject, body)


if __name__ == "__main__":
    # 测试发送（需先在 .env 或环境变量中配置）
    ok = notify_solve_error(0, 100)
    print("邮件发送成功" if ok else "未配置或发送失败，请设置 .env 或环境变量")