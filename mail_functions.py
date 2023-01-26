import my_umail as umail
import utime
import machine
import config
import uos
import gc


def send_alarm(alarm_msg):

    counter = 0

#    smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
    smtp = umail.SMTP('smtp.gmail.com', 587)
    utime.sleep(1)

    while True:
        counter +=1

        try:
            test1 = smtp.login('your_email@gmail.com', 'your 2 factor auth')

            result = str(test1).find('Accepted')

            if (result != -1):
                print('login OK')
                counter = 0
                break
        except Exception:
         #  try to capture the failure
            try:
                with open('errors.txt', 'a') as outfile:
                    outfile.write('smtp.login did NOT work')
            except OSError:
                pass

        if (counter == 5):
             counter = 0

             machine.reset() #  start from sratch
 
    counter = 0 #  reset

    wdt_feed()
    
    utime.sleep(1)
#  use a list for multiple recipents, but probably can't use the To: lines
    smtp.to('your_email@gmail.com')
    utime.sleep(1)
    smtp.write('From: your_email@gmail.com\n')
    smtp.write('To: your_email@gmail.com\n') #  gets rid of the bcc line
    smtp.write('Subject:My alarm\n')
    smtp.write(alarm_msg + '\n')
#    smtp.write('...\n') #  suppose to be important??
    smtp.send() #  does the proper ending
    smtp.quit()

    print('alarm has been sent')


def send_csv(date):
    file_size = uos.stat('datalog.csv')[6]
    chunk_size = 1024
    counter = 0
    content = 'there is no content' #  if reading ramdisk fails this keeps things alive


#    smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
    smtp = umail.SMTP('smtp.gmail.com', 587)
    utime.sleep(1)

    while True:
        counter +=1

        try:
            test1 = smtp.login('your_email@gmail.com', 'your 2 factor auth')

            result = str(test1).find('Accepted')

            if (result != -1):
                print('login OK')
                counter = 0
                break
        except Exception:
         #  try to capture the failure
            try:
                with open('errors.txt', 'a') as outfile:
                    outfile.write('smtp.login did NOT work')
            except OSError:
                pass

        if (counter == 5):
            counter = 0

            machine.reset() #  start from sratch

    counter = 0 #  reset

    
    utime.sleep(1)
    smtp.to('your_email@gmail.com')
    utime.sleep(1)
    smtp.write('From: your_email@gmail.com\n')
    smtp.write('To: your_email@gmail.com\n')
    smtp.write('Subject: Today\'s ' + config.device + 'datalog\n')
    smtp.write('MIME-Version: 1.0\n')
    smtp.write('Content-type: multipart/mixed; boundary=12345678900987654321\n')

    smtp.write('--12345678900987654321\n')
    smtp.write('Content-Type: text/plain; charset=utf-8\n')
    smtp.write('see attachment\n')
    smtp.write('--12345678900987654321\n')

 #  build today's filename into Content-Type and Content-Disposition
    csv_file = config.device + date + '.csv\n'

    content_type = 'Content-Type: text/csv; name=' + csv_file
    content_disposition = 'Content-Disposition: attachment; filename=' + csv_file 
    smtp.write(content_type)
    smtp.write(content_disposition)

   
 #  send data in 1024 chunks
    try:
        with open('datalog.csv', 'rb') as file:
            for chunk in range(0, file_size, chunk_size):
                this_chunk_size = min(chunk_size, file_size-chunk)
             #  handles the last dangling chunk that would be smaller than the full 1024 bytes
                smtp.write(file.read(this_chunk_size))
    except OSError as error:
        try:
            with open('errors.txt', 'a') as outfile:
                outfile.write('error = ' + str(error) + '\n')
                outfile.write('did not handle datalog.csv properly' + '\n')
        except OSError:
            pass

    smtp.send() # does the proper ending
    smtp.quit()

    print('log has been sent')
