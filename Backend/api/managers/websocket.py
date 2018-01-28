from PIL import Image
import websocket
import cStringIO
import base64
 
class WSClient():
 
    def __init__(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp("ws://172.30.177.39:8888/ws",
        on_message = self.on_message,
        on_error = self.on_error,
        on_close = self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever()
 
    def on_message(self, ws, message):
        image_string = cStringIO.StringIO(base64.b64decode(message))
        image = Image.open(image_string)
        image.show()
 
    def on_error(self, ws, error):
        print error
 
    def on_close(self, ws):
        print "connection closed"
 
    def on_open(self, ws):
        print "connected"
 
if __name__ == "__main__":
    client = WSClient()