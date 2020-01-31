import pika
import numpy as np
import os
import sys, signal
import visdom

vis = visdom.Visdom();
startTime=0;

def signal_handler(signal, frame):
    print("\nprogram exiting gracefully")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def unpackNameAndData(data):
	fmt = "8s" + str(len(data)-8) + "f"
	o = struct.unpack(fmt,data)
	return o

def nparray_callback(ch, method, props, body):
	global startTime;
	o = unpackNameAndData(body);
	samples = o(1)	
	t = np.arange(startTime,startTime+len(samples))/len(samples)
	vis.line(X=t, Y=samples,update='append')
	


rmquser = os.environ['RABBITMQ_USERNAME']
rmqpass = os.environ['RABBITMQ_PASSWORD']
queue = "eeg"
credentials = pika.PlainCredentials(rmquser,rmqpass)

connection = pika.BlockingConnection(pika.ConnectionParameters('10.0.0.12',credentials=credentials))
channel = connection.channel()

channel.basic_consume(queue=queue, on_message_callback=nparray_callback, auto_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')

channel.start_consuming()



