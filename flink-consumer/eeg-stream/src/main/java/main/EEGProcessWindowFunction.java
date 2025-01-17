package eegstreamer.process;

import eegstreamer.utils.EEGHeader;

import java.util.Arrays;
import java.util.stream.Collectors;

import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;
import org.apache.flink.streaming.api.functions.windowing.ProcessAllWindowFunction.Context;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;



public class EEGProcessWindowFunction
	extends ProcessWindowFunction<Tuple3<Integer,EEGHeader,float[]>, Tuple2<EEGHeader, float[]>, String, TimeWindow> {
	final static Logger log = LogManager.getLogger(EEGProcessWindowFunction.class.getName());
		
	private float windowLengthInSec = 0;
	private float windowOverlap = 0;
	
	public EEGProcessWindowFunction setWindowLength(float newLength){		
		this.windowLengthInSec = newLength;
		return this;
	}
	
	public EEGProcessWindowFunction setWindowOverlap(float newLength){
		this.windowOverlap = newLength;
		return this;
	}	
	
	@Override
	public void process(String key, 
						Context context, 
						Iterable<Tuple3<Integer,EEGHeader,float[]>> frames, 
						Collector<Tuple2<EEGHeader, float[]>> out)
			throws Exception
	{	
		// This function windows the data in the frames and sends them on their way
		long numMsgs = frames.spliterator().getExactSizeIfKnown();		
		float[] data= new float[0];
		int lastIdx = 0; //remembers the last index that was processed
		int frameLen = 0; //length of each frame (should be 250 during testing)
		int idx = 0;	//just for doing business on first frame
		EEGHeader header = new EEGHeader();
		// get the actual float data from each frame
		// and combine it into one long array that can be subsectioned
		for(Tuple3<Integer,EEGHeader,float[]> frame: frames){
			//grab data (for convenience)
			float[] frameData = frame.f2;
			//grab the last index (the new starting point)
			//and the header data
			if(idx==0){
				lastIdx = frame.f0;
				frameLen = frameData.length;
			}
			header = frame.f1;
			//get the current lenth of the data array
			int prevLength = data.length;
			//make a new copy of the data array that will allow pasting
			//in this frame's data
			data = Arrays.copyOf(data, data.length+frameData.length);
			System.arraycopy(frameData, 0, data,prevLength,frameData.length);
			idx++;
			log.debug("=====================================");
		    log.debug(String.format("user name   : %s", header.user_name));
        	log.debug(String.format("frame number: %d", header.frame_number));
        	log.debug(String.format("timestamp   : %d", header.time_stamp));
        	log.debug(String.format("ML Model    : %s", header.ML_model));
        	log.debug(String.format("samplingrate: %d", header.sampling_rate));
        	log.debug(String.format("num channels: %d", header.num_channels));
        	log.debug(String.format("num samples : %d", header.num_samples));
        	log.debug(String.format("    %s",header.channel_names));
        	log.debug("=====================================");
		}
		if(numMsgs==1)
			frameLen=0;
		// find which channel is the time channel so it can be used for correct timestamping
		// it is not guaranteed to be channel 0, nor is it guaranteed to exist
		String timeString = "time";
		for(String s : header.channel_names){
			if(s.toLowerCase().equals("time")){
				timeString = s;
				break;
			}
		}
		int timeChanIdx = header.channel_names.indexOf(timeString);
		
		// create a sliding window along the data and push that to stream out
		int startIdx=lastIdx;		
		int numChannels = header.num_channels; // need number of channels for proper spacing		
		int chunkNum=0;
		int windowLength = (int)(windowLengthInSec*header.sampling_rate);
		int strideLength = (int)((1-windowOverlap)*windowLengthInSec*header.sampling_rate + .5);		
		while(startIdx + windowLength*numChannels < data.length){			
			float[] tmp = Arrays.copyOfRange(data,startIdx,startIdx+windowLength*numChannels);
			// set the time stamp for this window to the value of the first sample in the time series
			if(timeChanIdx!=-1){ //if there is a time channel
			// Data is organized as [c0s0, c1s0, c2s0...,c0s1,c1s1,c2s1...]
			// so the first sample of the time channel is just the idx of the time channel
				header.time_stamp = (int)tmp[timeChanIdx]; 
			}			
			else{ 
				// if there's no time channel, use the frame number, sampling rate, and 
				//		number of samples to construct the timestamp
				
				// base time = frame number * number of ms in a frame
				// ms/frame = samples/s  /  samples/frame * 1000 ms/s
				// num_ms_frame = sampling_rate / num_samples in a frame * 1000
				int base_time = header.frame_number * (header.sampling_rate/header.num_samples*1000);
				// ms since start of frame = startIdx/sampling_rate * 1000
				int cur_time = (startIdx/numChannels)/header.sampling_rate*1000;
				header.time_stamp = base_time + cur_time;
			
			}
			out.collect(new Tuple2(header,tmp));
			// multiply by number of channels to move proper number of values forward
			startIdx = startIdx + strideLength*numChannels;
			chunkNum++;
		}
		startIdx -= frameLen; // since the front frame will drop off, subtract it's length from startIdx

		for(Tuple3<Integer, EEGHeader, float[]> frame: frames){
			frame.f0 = startIdx;
		}
	}
}

