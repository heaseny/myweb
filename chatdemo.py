#!/usr/bin/env python
#coding:utf-8
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpserver
import tornado.websocket
import logging
import uuid
import time
import datetime
import os.path


from tornado.options import define, options

define("port", default=8888, help="run on the specified port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/",Main),
            (r"/ly",MainHandler),
            (r"/chatsocket",ChatSocketHandler),
        ]
        settings = dict(
        cookie_secret = "you_cant_guess",
        template_path = os.path.join(os.path.dirname(__file__), "templates"),
        static_path = os.path.join(os.path.dirname(__file__),"static"),
        xsrf_cookies = True,
        debug = True,
        )
        super(Application,self).__init__(handlers, **settings)

class Main(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("ly.html",messages=ChatSocketHandler.cache, username="游客%d"%ChatSocketHandler.client_id)
class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    client_id = 1
    waiters = set()
    cache = []
    cache_size = 200

    @classmethod
    def update_cache(cls,chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    def open(self):
        self.client_id = ChatSocketHandler.client_id
        ChatSocketHandler.client_id += 1
        ChatSocketHandler.waiters.add(self)
    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    def on_message(self,message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        print("parsed:{}".format(parsed))
        self.username = parsed["username"]
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
            "type": "message",
            "client_id": self.client_id,
            "username": self.username,
            "datetime":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)
    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d waiters",len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exec_info=True)
def main():
    tornado.options.parse_command_line()
    httpserver = tornado.httpserver.HTTPServer(Application())
    httpserver.bind(options.port)
    httpserver.start(1)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()

