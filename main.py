import json
import requests
import time
import boto3

aws_access_key_id = None
aws_secret_access_key = None
aws_region = None
aws_bucket = None


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


def main():
    get_credentials()
    job_name = raw_input('Enter the job name, please: ')
    wav_file_path = raw_input('Audio path (.wav): ')
    wav_file_name = str(wav_file_path.split('\\')[-1:][0])

    print ('Putting audio in S3')
    put_in_s3(local_path=wav_file_path, remote=wav_file_name)

    print ('Creating AWS Transcribe job')
    transcribe = start_job(job_name, wav_file_name)

    print ('Waiting for transcribe')
    print get_transcribe(transcribe, job_name)


if __name__ == '__main__':
    main()