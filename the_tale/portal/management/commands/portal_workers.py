# coding: utf-8
import os
import time
import subprocess

from optparse import make_option

from django.core.management.base import BaseCommand

from dext.utils import pid

from portal.workers.environment import workers_environment

def start():
    with open(os.devnull, 'w') as devnull:
        subprocess.Popen(['./manage.py', 'accounts_registration'], stdin=devnull, stdout=devnull, stderr=devnull)

    print 'infrastructure started'

def stop():
    if pid.check('accounts_registration'):
        print 'registration found, send stop command'
        workers_environment.registration.cmd_stop()
        print 'waiting answer'
        answer_cmd = workers_environment.registration.stop_queue.get(block=True)
        answer_cmd.ack()
        print 'answer received'

    while (pid.check('accounts_registration')):
        time.sleep(0.1)

    print 'infrastructure stopped'


class Command(BaseCommand):

    help = 'run infrastructure workers'

    requires_model_validation = False

    option_list = BaseCommand.option_list + ( make_option('-c', '--command',
                                                          action='store',
                                                          type=str,
                                                          dest='command',
                                                          help='start|stop|restart|status'),
                                              )

    @pid.protector('game_workers')
    def handle(self, *args, **options):
        command = options['command']

        if command == 'start':
            start()
        elif command == 'stop':
            stop()
        elif command == 'force_stop':
            pid.force_kill('accounts_registration')
            print 'infrastructure stopped'

        elif command == 'restart':
            start()
            stop()
            print 'infrastructure restarted '

        elif command == 'status':
            print 'command "%s" does not implemented yet ' % command

        else:
            print 'command did not specified'
