import json
import requests
import time
import boto3
import pyaudio
import wave
from datetime import datetime
import os

aws_access_key_id = None
aws_secret_access_key = None
aws_region = None
aws_bucket = None


def record_audio(seconds, wav_file_name):
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    CHUNK = 1024

    audio = pyaudio.PyAudio()

    # start Recording
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    print "Start recording..."
    frames = []

    for i in range(0, int(RATE / CHUNK * seconds)):
        data = stream.read(CHUNK)
        frames.append(data)

    # stop Recording
    print "Finished recording"
    stream.stop_stream()
    stream.close()
    audio.terminate()

    waveFile = wave.open('audios\\' + wav_file_name, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()


def put_in_s3(local_path, remote):
    _bucket = boto3.resource('s3',
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key
                             ).Bucket(aws_bucket)
    _bucket.put_object(Key=remote, Body=open(local_path, 'rb'))


def start_job(job_name, remote_file):
    transcribe = boto3.client('transcribe',
                              aws_region,
                              aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key)

    job_uri = "https://s3.amazonaws.com/{bucket}/{file}".format(bucket=aws_bucket,
                                                                file=remote_file)

    transcribe.start_transcription_job(TranscriptionJobName=job_name,
                                       Media={'MediaFileUri': job_uri},
                                       MediaFormat='wav',
                                       LanguageCode='en-US')

    return transcribe


def get_transcribe(transcribe, job_name):
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Not ready yet...")
        time.sleep(5)

    request = requests.get(status['TranscriptionJob']['Transcript']['TranscriptFileUri'])
    response = request.text
    response = json.loads(response)
    return response['results']['transcripts'][0]['transcript']


def get_credentials():
    tmp = raw_input('Enter AWS access key ID: ')
    if tmp != '':
        global aws_access_key_id
        aws_access_key_id = tmp

    tmp = raw_input('Enter AWS secret access key: ')
    if tmp != '':
        global aws_secret_access_key
        aws_secret_access_key = tmp

    tmp = raw_input('Enter AWS default region: ')
    if tmp != '':
        global aws_region
        aws_region = tmp

    tmp = raw_input('Enter AWS S3 bucket: ')
    if tmp != '':
        global aws_bucket
        aws_bucket = tmp


def get_audio():
    for i in range(3):
        choice = raw_input('Do you want to record an audio? (y/n) ')
        if choice == 'y':
            wav_seconds = int(raw_input('Type the audio length (seconds): '))
            wav_filename = raw_input('Type the audio title: ')
            wav_filename += datetime.now().strftime('%Y%m%d-%H%M%S') + '.wav'

            record_audio(wav_seconds, wav_filename)

            return os.path.dirname(os.path.abspath(__file__)) + '\\audios\\' + wav_filename
        elif choice == 'n':
            wav_path = raw_input('Please, enter the audio path: ')
            return wav_path

    print ('No option was chosen')
    print ('The execution will be finished')
    exit(1)


def main():
    get_credentials()
    job_name = raw_input('Enter the job name, please: ')
    wav_path = get_audio()
    wav_filename = str(wav_path.split('\\')[-1:][0])
    print wav_filename

    print ('Putting audio in S3')
    put_in_s3(local_path=wav_path, remote=wav_filename)

    print ('Creating AWS Transcribe job')
    transcribe = start_job(job_name, wav_filename)

    print ('Waiting for transcribe')
    print get_transcribe(transcribe, job_name)


if __name__ == '__main__':
    main()