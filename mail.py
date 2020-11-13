import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header



def send_mail():
    
    mail_host = "smtp.126.com"  
    mail_user = "dj259753@126.com" 
    mail_pass = "dj970710"  
     
    sender = 'dj259753@126.com'  
    receivers = 'dj259753@126.com'


    message = MIMEMultipart()
    message['From'] = Header("dj259753@126.com", 'utf-8')
    message['To'] =  Header("dj259753@126.com")
    subject = 'Weekly report of Fruit ripening monitoring'
    message['Subject'] = Header(subject, 'utf-8')
     
    #message 
    message.attach(MIMEText('Dear sir,\nThis is your report of fruit ripening monitoring, please check.\n\nRegards,\nJin.', 'plain', 'utf-8'))
     
    #att1
    att1 = MIMEText(open('Fruit_decay.csv', 'rb').read(), 'base64', 'utf-8')
    att1["weekly report"] = 'application/octet-stream'
    
    att1["weekly report"] = 'attachment; filename="Fruit ripening monitoring.csv"'
    message.attach(att1)
    
    att2 = MIMEText(open('Fruit_reading.csv', 'rb').read(), 'base64', 'utf-8')
    att2["fruit report"] = 'application/octet-stream'
    att2["fruit report"] = 'attachment; filename="Fruit identification.csv"'
    message.attach(att2)
    
    
    
        
    try:
        smtpObj = smtplib.SMTP_SSL(mail_host, 465)  # SSL, port = 465
        smtpObj.login(mail_user, mail_pass)  
        smtpObj.sendmail(sender, receivers, message.as_string())  
        print("mail has been send successfully.")
    except smtplib.SMTPException as e:
        print(e)
