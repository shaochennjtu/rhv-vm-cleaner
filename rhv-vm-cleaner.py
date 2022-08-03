from __future__ import print_function
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import datetime as datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    return {
        'raw': raw_message.decode("utf-8")
    }

def send_mail(service, raw_message):
    service.users().messages().send(userId='me', body=raw_message).execute()

def parse_date(date_list):
    new_date_list = []
    for date_time in date_list:
        new_date_list.append(str(date_time).split(' ')[0])
    return new_date_list

def generate_last_dates(num_of_days):
    base = datetime.datetime.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(num_of_days)]
    return parse_date(date_list)

def arrange_vms(vm):
    vm_stats = []
    vm_stop_date = []
    vm_stop_date.append(vm._stop_time)
    vm_stats = parse_date(vm_stop_date)
    vm_stats.append(vm.name)
    return vm_stats

def verify_date(date, valid_dates):
    for valid_date in valid_dates:
        if date == valid_date:
            return False
    return True

def delete_vm(vm_name, vms_service):
    vm_string = "name=" + vm_name
    print(vm_string)
    vm = vms_service.list(search=vm_string)[0]
    service = vms_service.vm_service(vm.id)
    service.remove()

def main():
    connection = sdk.Connection(
        url='<RHV-URL>',
        username='<user with delete permissions>',
        password='<user with delete permissions>',
        insecure=True,
    )

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    vms_service = connection.system_service().vms_service()
    virtual_machines = vms_service.list()
    last_days = generate_last_dates(10)
    delete_vms = []
    bot_email = "<bot@email.com>"

    if len(virtual_machines) > 0:
        for virtual_machine in virtual_machines:
            stat = arrange_vms(virtual_machine)
            if str(virtual_machine.status) == "down":
                msg_subject = "The RHV Environment requires your attention"
                msg_text = "\
                Dear " + virtual_machine.comment + ",\n\n \
                Your VM - " + str(virtual_machine.name) + " has been turned off. \n \
                The VM will be deleted in the next few days. \n \
                Take care of your VM. Either delete it or turn it on. \n\n \
                Best Regards,\n \
                The RHV BOT."
                send_mail(service, create_message(bot_email, virtual_machine.comment, msg_subject, msg_text))
                if stat[1] != "HostedEngine":
                    if verify_date(stat[0], last_days):
                        msg_subject = "RHV Environment announcement"
                        msg_text = "\
                        Dear " + virtual_machine.comment + ",\n\n \
                        Your VM - " + str(virtual_machine.name) + " has been deleted. \n \
                        Best Regards,\n \
                        The RHV BOT."
                        send_mail(service, create_message(bot_email, virtual_machine.comment, msg_subject, msg_text))
                        delete_vms.append(stat[1])

    for vm in delete_vms:
        delete_vm(vm, vms_service)

if __name__ == '__main__':
    main()
