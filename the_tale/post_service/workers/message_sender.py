# coding: utf-8
import time
import Queue
import datetime

from django.utils.log import getLogger

from common.amqp_queues import connection, BaseWorker

from post_service.prototypes import MessagePrototype
from post_service.conf import post_service_settings


class MessageSenderException(Exception): pass

class Worker(BaseWorker):

    def __init__(self, messages_queue, stop_queue):
        super(Worker, self).__init__(logger=getLogger('post_service.workers.message_sender'), command_queue=messages_queue)
        self.stop_queue = connection.SimpleQueue(stop_queue)
        self.initialized = True
        self.next_message_process_time = datetime.datetime.now()

    def clean_queues(self):
        super(Worker, self).clean_queues()
        self.stop_queue.queue.purge()

    def initialize(self):
        self.logger.info('MESSAGE SENDER INITIALIZED')

    def run(self):

        while not self.exception_raised and not self.stop_required:
            try:
                cmd = self.command_queue.get_nowait()
                cmd.ack()
                self.process_cmd(cmd.payload)
            except Queue.Empty:
                if self.next_message_process_time < datetime.datetime.now():
                    if not self.send_messages():
                        self.next_message_process_time = datetime.datetime.now() + datetime.timedelta(seconds=post_service_settings.MESSAGE_SENDER_DELAY)
                time.sleep(1.0)

    def send_messages(self):
        self.logger.info('search for unprocessed messages')

        message = MessagePrototype.get_priority_message()

        if message is None:
            return False

        self.logger.info('process message %s' % message.uid)

        message.process()

        if message.state._is_PROCESSED:
            self.logger.info('message %s status %s' % (message.uid, message.state))
        else:
            self.logger.error('message %s status %s ' % (message.uid, message.state))

        return True


    def cmd_stop(self):
        return self.send_cmd('stop')

    def process_stop(self):
        self.initialized = False
        self.stop_required = True
        self.stop_queue.put({'code': 'stopped', 'worker': 'message_sender'}, serializer='json', compression=None)
        self.logger.info('MESSAGE SENDER STOPPED')
