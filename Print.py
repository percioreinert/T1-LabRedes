import datetime


class Print:
    def __init__(self, ip: str, name: str, time: datetime.datetime):
        self.ip = ip
        self.name = name
        self.time = time