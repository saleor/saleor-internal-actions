from templated_email import send_templated_mail

from saleor.celeryconf import app
from saleor.core.emails import get_email_context


@app.task
def send_password_email(user, password):
    send_kwargs, ctx = get_email_context()
    ctx["password"] = password
    send_templated_mail(
        template_name="dashboard/staff/password",
        recipient_list=[user.email],
        context=ctx,
        **send_kwargs,
    )
