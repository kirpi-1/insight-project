import pika
import os
import time
import sys, signal
import numpy as np
import numpy.matlib
import uuid
import struct
import visdom
import json
sys.path.append('../utils/')
from DataPackager import makeHeader,packHeaderAndData
import RMQUtils
import time

def signal_handler(signal, frame):
	print("\nprogram exiting gracefully")
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

parser = RMQUtils.getParser()
args = parser.parse_args()


#rmquser = os.environ['RABBITMQ_USERNAME']
#rmqpass = os.environ['RABBITMQ_PASSWORD']
cred = pika.PlainCredentials(args.RMQuser,args.RMQpassword)
rmqIP = args.RMQhost
userName = args.RMQuser
year_begin = int(time.mktime(time.struct_time((2020,1,1,0,0,0,0,1,0))))
now = int(time.mktime(time.gmtime()))
sessionID = args.RMQuser+str(now-year_begin)#+str(uuid.uuid4())
routing_key=args.RMQqueue
#corr_id = str(uuid.uuid4())
rmqargs = dict()
rmqargs['x-message-ttl']=10000

params = pika.ConnectionParameters(	host=rmqIP, \
									port=args.RMQport,\
									credentials=cred, \
									virtual_host=args.RMQvhost)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue=routing_key,arguments=rmqargs,durable = True)
#props = pika.BasicProperties(correlation_id=corr_id)

startTime = 0;
freqs = [1,4,11,22,35,80];
fullCycle=10
print("Sending messages. CTRL+C to quit.")
plotTime = np.zeros((args.sampling_rate*4))
plotSignal = np.zeros((args.sampling_rate*4))

#vis = visdom.Visdom()
#linwin = visdom.line([0])

def makeSignal(t, freqs,cyclingFreq = 11):
	signal = np.zeros(t.size)
	for f in freqs:
		signal = signal + np.cos(2*np.pi*t*f)+np.random.randn(t.size)
	cycleTime = t % fullCycle - fullCycle/2
	signal = signal + 2*np.cos(2*np.pi*t*11)*(cycleTime/fullCycle)	
	signal = signal / len(freqs); #normalize
	return signal

#vis = visdom.Visdom()
#win = vis.line(X=plotTime, Y=plotSignal)
frameNumber = 0;
while(True):
	t = np.arange(startTime,startTime+args.sample_time,1/args.sampling_rate,dtype=np.float32)
	signal = np.zeros((len(t),args.num_chan+1))
	signal[:,0] = t*1000 # miliseconds
	channelNames = list();
	channelNames.append('time');
	for c in np.arange(args.num_chan):
		signal[:,c+1] = makeSignal(t, freqs, args.cycle_freq)
		channelNames.append(str(c))
		
	header = makeHeader(userName = userName, sessionID = sessionID,\
						frameNumber = frameNumber, timeStamp = int(startTime*1000),\
						channelNames = channelNames, numSamples=args.sampling_rate*args.sample_time,\
						numChannels=signal.shape[1])
	print(header)

	frame = packHeaderAndData(header,signal)
	#headerSize = int.from_bytes(frame[0:3],byteorder='little')	
	#vis.line(win=linwin,Y=signal[0,:])	
	#print("frame length is:", len(frame))
	#print("4 + {} + {} = {}".format(headerSize,sampleSize,4+headerSize+sampleSize))
	
	channel.basic_publish(exchange=args.RMQexchange,
						routing_key=routing_key,
						body=frame)
						#properties=props,

	startTime = startTime+1
	frameNumber = frameNumber + 1
	time.sleep(args.sample_time)
	#x = input();

