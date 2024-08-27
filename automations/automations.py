from requests_html import HTMLSession
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ..utils.task_manager import automation


@automation(3, "check_ipad_stock", False)
def check_ipad_stock():
    session = HTMLSession()
    URL = "https://www.apple.com/shop/refurbished/ipad/ipad-pro-12-9"


    r = session.get(URL)

    r.html.render(sleep=1) # you can use r.html.render(sleep=1) if you want

    # Step 2: Parse the Data
    # Assuming that the relevant iPad model info is contained in a specific tag/class
    # You may need to inspect the HTML of the webpage to fine-tune this selectio/n


    available_models = []
    ipad_items = r.html.find(".rf-refurb-producttiles")
    for item in ipad_items:
        titles = item.find('h3')
        for title in titles:
            if any(gen in title.text.strip() for gen in ['6th', '7th', '8th']):
                available_models.append(title.text.strip())

    # Step 3: Check if Desired Models Are Available
    if available_models:
        # Step 4: Send an Email Notification
        sender_email = "tskook@icloud.com"
        receiver_email = "t.shlomi@icloud.com"
        password = "ryim-mpuk-dvav-cxfp"
        username = "t.shlomi"

        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = "Refurbished iPads Available"

        body = "The following refurbished iPads are available:\n\n" +"{',\n'.join(available_models)}\n\nGO!!:  {URL}"
        message.attach(MIMEText(body, 'plain'))

        # Create SMTP session for sending the mail
        try:
            server = smtplib.SMTP('smtp.mail.me.com', 587)  # Replace with your SMTP server details
            server.starttls()
            server.login(username, password)
            text = message.as_string()
            server.sendmail(sender_email, receiver_email, text)
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
    else:
        print("No desired iPad models found.")