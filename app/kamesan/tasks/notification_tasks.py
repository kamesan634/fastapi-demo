"""
通知相關背景任務

提供各種通知發送的背景任務。

任務：
- send_email: 發送電子郵件
- send_order_confirmation: 發送訂單確認通知
- send_welcome_email: 發送歡迎郵件
"""

from typing import Optional

from app.kamesan.tasks.celery_app import celery_app


@celery_app.task(name="app.kamesan.tasks.notification_tasks.send_email")
def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> dict:
    """
    發送電子郵件

    使用 SMTP 發送電子郵件。

    參數:
        to: 收件人 Email
        subject: 郵件主旨
        body: 郵件內容（純文字）
        html_body: 郵件內容（HTML，可選）

    回傳值:
        dict: 發送結果
    """
    print(f"發送郵件至 {to}...")
    print(f"主旨: {subject}")

    # TODO: 實作實際的郵件發送
    # import smtplib
    # from email.mime.text import MIMEText
    # from email.mime.multipart import MIMEMultipart
    #
    # msg = MIMEMultipart("alternative")
    # msg["Subject"] = subject
    # msg["From"] = settings.SMTP_FROM
    # msg["To"] = to
    #
    # part1 = MIMEText(body, "plain")
    # msg.attach(part1)
    #
    # if html_body:
    #     part2 = MIMEText(html_body, "html")
    #     msg.attach(part2)
    #
    # with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
    #     server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    #     server.sendmail(settings.SMTP_FROM, to, msg.as_string())

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
    }


@celery_app.task(name="app.kamesan.tasks.notification_tasks.send_order_confirmation")
def send_order_confirmation(order_id: int, customer_email: str) -> dict:
    """
    發送訂單確認通知

    當訂單建立成功後，發送確認郵件給客戶。

    參數:
        order_id: 訂單 ID
        customer_email: 客戶 Email

    回傳值:
        dict: 發送結果
    """
    print(f"發送訂單 {order_id} 確認通知至 {customer_email}...")

    subject = f"訂單確認 - 訂單編號 #{order_id}"
    body = f"""
親愛的顧客您好：

感謝您的訂購！您的訂單已成功建立。

訂單編號: #{order_id}

如有任何問題，請聯繫我們的客服團隊。

祝您購物愉快！

FastAPI Demo 團隊
    """

    return send_email(customer_email, subject, body)


@celery_app.task(name="app.kamesan.tasks.notification_tasks.send_welcome_email")
def send_welcome_email(user_email: str, user_name: str) -> dict:
    """
    發送歡迎郵件

    新會員註冊後發送歡迎郵件。

    參數:
        user_email: 會員 Email
        user_name: 會員名稱

    回傳值:
        dict: 發送結果
    """
    print(f"發送歡迎郵件至 {user_email}...")

    subject = "歡迎加入 FastAPI Demo！"
    body = f"""
親愛的 {user_name} 您好：

歡迎加入 FastAPI Demo！

我們很高興您成為我們的會員。現在您可以享受以下優惠：

- 首次消費 9 折優惠
- 每消費 100 元累積 1 點
- 生日當月雙倍積點

開始探索我們的商品吧！

FastAPI Demo 團隊
    """

    return send_email(user_email, subject, body)
