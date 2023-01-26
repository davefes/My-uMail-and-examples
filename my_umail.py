# uMail (MicroMail) for MicroPython
# Copyright (c) 2018 Shawwwn <shawwwn1@gmai.com>
# License: MIT

# Changes:
# - added debugging
# - DEFAULT_TIMEOUT = 30

# 26 Jan 2023 D.Festing


import usocket
import utime
import machine
import config 


DEFAULT_TIMEOUT = 30 # was 10 sec
LOCAL_DOMAIN = '127.0.0.1'
CMD_EHLO = 'EHLO'
CMD_STARTTLS = 'STARTTLS'
CMD_AUTH = 'AUTH'
CMD_MAIL = 'MAIL'
AUTH_PLAIN = 'PLAIN'
AUTH_LOGIN = 'LOGIN'

class SMTP:
    def cmd(self, cmd_str):
        sock = self._sock;
        sock.write('%s\r\n' % cmd_str)
        resp = []
        next = True
        while next:
            code = sock.read(3)
            next = sock.read(1) == b'-'
            resp.append(sock.readline().strip().decode())

        if (config.debug is True):
            try:
                with open('errors.txt', 'a') as outfile:
                    outfile.write(str(code) + '\n')
            except OSError:
                pass

        return int(code), resp

    def __init__(self, host, port, ssl=False, username=None, password=None):
        import ussl
        self.username = username
        counter = 0

        while True:
            counter +=1

            try:
                addr = usocket.getaddrinfo(host, port)[0][-1]
                break
            except OSError as err:
                if err.args[0] == -202: #  no network available
                    try:
                        with open('errors.txt', 'a') as outfile:
                            outfile.write('no network available' + '\n')
                    except OSError:
                        pass
            except Exception:
                try:
                    with open('errors.txt', 'a') as outfile:
                        outfile.write('socket.getaddrinfo() failed' + '\n')
                except OSError:
                    pass

            if (counter == 5):
                counter = 0

                machine.reset() #  start from sratch

            utime.sleep(5)

        counter = 0 #  reset counter

        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)

        while True:
            counter +=1

            try:
                sock.connect(addr)
                break
            except OSError as err:
                if err.args[0] == 116: #  socket.timeout
                    try:
                        with open('errors.txt', 'a') as outfile:
                            outfile.write('socket timed-out' + '\n')
                    except OSError:
                        pass
            except Exception:
                try:
                    with open('errors.txt', 'a') as outfile:
                        outfile.write('socket.connect() failed' + '\n')
                except OSError:
                    pass

            if (counter == 5):
                counter = 0

                machine.reset() #  start from sratch

            utime.sleep(5)

        counter = 0 #  reset
        code = 0 #  reset

        while ((counter < 5) and (code != 220)):
            counter +=1

            if ssl:
                sock = ussl.wrap_socket(sock)
                print('SSL OK')

                try:
                    with open('errors.txt', 'a') as outfile:
                        outfile.write('SSL try number = ' +str(counter) + '\n')
                except OSError:
                    pass

            code = int(sock.read(3))

            utime.sleep(1)

        if (counter == 5):
            counter = 0

            machine.reset() #  start from sratch

        counter = 0 #  reset

        sock.readline()
        assert code==220, 'cant connect to server %d, %s' % (code, resp)
        self._sock = sock

        code = 0 #  reset

        while ((counter < 5) and (code != 220)):
            counter +=1

            code, resp = self.cmd(CMD_EHLO + ' ' + LOCAL_DOMAIN)
            assert code==250, '%d' % code

            if CMD_STARTTLS in resp:
                code, resp = self.cmd(CMD_STARTTLS)
                print('STARTTLS OK')

                if (config.debug is True):
                    try:
                        with open('errors.txt', 'a') as outfile:
                            outfile.write('TLS try number = ' +str(counter) + '\n')
                    except OSError:
                        pass

                assert code==220, 'start tls failed %d, %s' % (code, resp)
                self._sock = ussl.wrap_socket(sock)

                utime.sleep(1)

        if (counter == 5):
            counter = 0

            machine.reset() #  start from sratch

        counter = 0 #  reset

        if username and password:
            self.login(username, password)

    def login(self, username, password):
        self.username = username
        code, resp = self.cmd(CMD_EHLO + ' ' + LOCAL_DOMAIN)
        assert code==250, '%d, %s' % (code, resp)

        auths = None
        for feature in resp:
            if feature[:4].upper() == CMD_AUTH:
                auths = feature[4:].strip('=').upper().split()
        assert auths!=None, "no auth method"

        from ubinascii import b2a_base64 as b64
        if AUTH_PLAIN in auths:
            cren = b64("\0%s\0%s" % (username, password))[:-1].decode()
            code, resp = self.cmd('%s %s %s' % (CMD_AUTH, AUTH_PLAIN, cren))
        elif AUTH_LOGIN in auths:
            code, resp = self.cmd("%s %s %s" % (CMD_AUTH, AUTH_LOGIN, b64(username)[:-1].decode()))
            assert code==334, 'wrong username %d, %s' % (code, resp)
            code, resp = self.cmd(b64(password)[:-1].decode())
        else:
            raise Exception("auth(%s) not supported " % ', '.join(auths))

        assert code==235 or code==503, 'auth error %d, %s' % (code, resp)
        return code, resp

    def to(self, addrs, mail_from=None):
        mail_from = self.username if mail_from==None else mail_from
        code, resp = self.cmd(CMD_EHLO + ' ' + LOCAL_DOMAIN)
        assert code==250, '%d' % code
        code, resp = self.cmd('MAIL FROM: <%s>' % mail_from)
        assert code==250, 'sender refused %d, %s' % (code, resp)

        if isinstance(addrs, str):
            addrs = [addrs]
        count = 0
        for addr in addrs:
            code, resp = self.cmd('RCPT TO: <%s>' % addr)
            if code!=250 and code!=251:
                print('%s refused, %s' % (addr, resp))
                count += 1
        assert count!=len(addrs), 'recipient refused, %d, %s' % (code, resp)

        code, resp = self.cmd('DATA')
        assert code==354, 'data refused, %d, %s' % (code, resp)
        return code, resp

    def write(self, content):
        print(content)
        self._sock.write(content)

    def send(self, content=''):
        if content:
            self.write(content)
        self._sock.write('\r\n.\r\n') # the five letter sequence marked for ending
        line = self._sock.readline()
        return (int(line[:3]), line[4:].strip().decode())

    def quit(self):
        self.cmd("QUIT")
        self._sock.close()
