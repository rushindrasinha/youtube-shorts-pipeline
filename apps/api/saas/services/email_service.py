from saas.settings import settings

def send_email(to: str, subject: str, html_body: str):
    if settings.ENVIRONMENT == "development":
        print(f"[EMAIL] To: {to} | Subject: {subject}")
        return

def send_welcome_email(email: str, name: str):
    send_email(email, "Welcome to ShortFactory!", f"<h1>Welcome, {name}!</h1>")

def send_job_completed_email(email: str, topic: str, url: str):
    send_email(email, f"Short ready: {topic}", f"<a href='{url}'>View</a>")

def send_job_failed_email(email: str, topic: str, error: str):
    send_email(email, f"Short failed: {topic}", f"Error: {error}")

def send_team_invite_email(email: str, team: str, inviter: str, url: str):
    send_email(email, f"Join {team}", f"{inviter} invited you. <a href='{url}'>Accept</a>")
