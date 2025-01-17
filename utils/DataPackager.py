import struct
import json
import sys
import numpy as np
from datetime import datetime;

def packHeaderAndData(header, data):
	# header - dictionary of header items
	# data   - 2 dimensional numpy.array of signals, each column(dim 0) is a channel	
	j = json.dumps(header)
	headerSize = len(j)
	fmt = "<i"+str(headerSize) + "s" + str(header['num_channels']*header['num_samples']) + "f"
	o = struct.pack(fmt,headerSize,j.encode('utf-8'),*data.flatten())
	return o
	
def unpackHeaderAndData(message):
	headerSize = int.from_bytes(message[0:3],byteorder="little");
	# "<" is little-endian
	fmt = "<" + str(headerSize) + "s"
	# read starting from byte 4 since bytes 0-3 are header size int
	h = struct.unpack(fmt, message[4:headerSize+4])
	header = json.loads(h[0])
	# use header to determine size of actual data
	totalSamples = header['num_channels']*header['num_samples']
	fmt = "<" + str(totalSamples) + "f"
	d = np.array(struct.unpack(fmt, message[headerSize+4:]))
	data = d.reshape((header['num_samples'],header['num_channels']))
	return header, data	

def makeHeader(userName, frameNumber, timeStamp, channelNames, \
		numSamples,	numChannels, sessionID='', mlModel='default',\
		preprocessing="standard", sampling_rate=250, start_datetime=0):
	# start_datetime is a UTC datetime
	if(start_datetime==0):
		start_datetime = datetime.utcnow()
	if sessionID=='':
		sessionID = userName + str(start_datetime);
	h = dict()
	h['user_name']=str(userName)
	h['session_id']=str(sessionID)
	h['frame_number']=int(frameNumber)
	h['time_stamp']=int(timeStamp)
	h['year']   = int(start_datetime.year)
	h['month']  = int(start_datetime.month)
	h['day']    = int(start_datetime.day)
	h['hour']   = int(start_datetime.hour)
	h['minute'] = int(start_datetime.minute)
	h['second'] = int(start_datetime.second)
	h['microsecond'] = int(start_datetime.microsecond)
	h['ML_model']=str(mlModel)
	h['preprocessing']=str(preprocessing)
	h['sampling_rate']=int(sampling_rate)
	h['num_samples'] = int(numSamples)
	h['num_channels'] = int(numChannels)	
	if not type(channelNames) is list:
		raise TypeError("channel names must be a list")
	h['channel_names']=channelNames
	
	return h


def splitTimeAndEEG(header, data):
	timeIdx = 0;
	for i,n in enumerate(header['channel_names']):
		if n.lower()=='time':
			timeIdx=i;
			break;
	# get time data
	timeChan = np.expand_dims(data[:,timeIdx],axis=1)
	mask = np.ones(header['num_channels'],dtype=bool)
	mask[timeIdx]=False
	# extract just eeg data
	eeg = data[:,mask]
	return timeChan, eeg