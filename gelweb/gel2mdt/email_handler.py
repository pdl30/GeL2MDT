from django.utils.log import AdminEmailHandler
from django.core import mail


class ManagerEmailHandler(AdminEmailHandler):
    def send_mail(self, subject, message, *args, **kwargs):
        # mail.mail_managers(subject, '', *args, connection=self.connection(), **kwargs)
        # print(subject, message)
        msg = mail.EmailMessage(subject, '', 'gel2mdt.technicalsupport@nhs.net', ['bioinformatics@gosh.nhs.uk'])
        msg.send()

