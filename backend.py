import tornado.ioloop
import tornado.web
import tornado.websocket
import redis.asyncio as redis
import json
import uuid
import logging
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

chat_history = []


class ChatWebSocket(tornado.websocket.WebSocketHandler):
    clients = set()

    def open(self):
        self.user_id = str(uuid.uuid4())
        self.clients.add(self)

        logger.info(f"New user connected with ID: {self.user_id}")

        for message in chat_history:
            self.write_message(json.dumps(message))

        self.write_message(json.dumps({
            "type": "system",
            "message": f"Добро пожаловать в чат! Ваш пользовательский ID в этом чате: {self.user_id}"
        }))

    def on_message(self, message):
        logger.info(f"Message from {self.user_id}: {message}")

        data = {
            "type": "chat",
            "message": message,
            "user_id": self.user_id
        }
        asyncio.create_task(self.publish_to_redis(data))

        # Добавляем сообщение в историю
        chat_history.append(data)

    async def publish_to_redis(self, data):
        await redis_client.publish("chat", json.dumps(data))

    def on_close(self):
        self.clients.remove(self)
        logger.info(f"User {self.user_id} disconnected")


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/ws", ChatWebSocket),
    ])


async def listen_to_redis():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chat")

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            data = message['data']
            parsed_data = json.loads(data)

            logger.info(f"New message from Redis: {parsed_data}")

            for client in ChatWebSocket.clients:
                try:
                    client.write_message(json.dumps(parsed_data))
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    logger.info("Server started on http://localhost:8888")

    asyncio.get_event_loop().create_task(listen_to_redis())

    tornado.ioloop.IOLoop.current().start()
