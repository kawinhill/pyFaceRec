
import requests


class TokenErrorException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
    def __str__(self):
        return f"Error TOKEN - \"{self.message}\" "
    
class LineNotify:
    def __init__(self, token):
        self.token = token
        self.URL = "https://notify-api.line.me/api/notify"
        auth = "Bearer " + self.token
        self.headers = {"Authorization": auth}

    def sendMessage(self, message):
        data = {"message": message}
        session = requests.Session()
        res = session.post(self.URL, headers=self.headers, data=data)
        if res.status_code != 200:
            raise TokenErrorException(self.token)
    def sendImage(self,image, message):
        data = {"message": message}
        files = {"imageFile": image}
        session = requests.Session()
        res = session.post(self.URL, headers=self.headers, data=data, files=files)
        if res.status_code != 200:
            raise TokenErrorException(self.token)

ln = LineNotify("Skd0aP8M7WpxENlze6sSxKgllD93Bau9cbdQWacjEn2")
