import concurrent.futures
import os
import ffmpeg
import m3u8
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

file_option = input('Using online (0) or local (1) m3u8 file?: ')
if file_option == '0':
    file_option = False
    url = input('URL to be downloaded: ')
elif file_option == '1':
    file_option = True
    url = input('File path: ')
else:
    print('Invalid option. Exiting ...')
    exit(1)
    
HEADER = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept-Language':'en-US, en;q=0.9, *;q=0.5',
    'Accept-Encoding': 'gzip, br',
    'Referer': 'https://www.google.com/'
    }
output_filename = 'output.mp4'
filename_suffix = 0

while os.path.exists(output_filename):
    filename_suffix += 1
    output_filename = f'output({filename_suffix}).mp4'


def proccess_segment(segsurl, urlIndex):
    stream_encrypted = requests.get(segsurl.absolute_uri, headers=HEADER).content
    if indexObject.keys[0]:
        stream_decrypted = cipher.decrypt(stream_encrypted)
        stream_decrypted = unpad(stream_decrypted, AES.block_size)
        return urlIndex, stream_decrypted
    else:
        return urlIndex, stream_encrypted

ffmpeg_process = (
    ffmpeg.input('pipe:', format='mpegts')
    .output(output_filename, c='copy')
    .run_async(pipe_stdin=True)
)


indexObject = m3u8.loads(url) if file_option else m3u8.load(url)
segment_amount = len(indexObject.segments)
work_counter = 0
print(f'\n{segment_amount} segments to be downloaded.')

if indexObject.keys[0]:
    encryption_key = requests.get(indexObject.keys[0].absolute_uri, headers=HEADER).content
    cipher = AES.new(encryption_key, AES.MODE_CBC)


with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(proccess_segment, segment, idx) for idx, segment in enumerate(indexObject.segments)]
    results = [None] * segment_amount
    for completed in concurrent.futures.as_completed(futures):
        seg_idx, decrypted_data = completed.result()
        if decrypted_data:
            results[seg_idx] = decrypted_data
            work_counter += 1
            if work_counter != segment_amount:
                print(f'Progress: {work_counter}/{segment_amount} ({round(work_counter*100/segment_amount, 1)}%)', end='\r')
            else:
                print(f'Progress: {work_counter}/{segment_amount} ({round(work_counter*100/segment_amount, 1)}%)\n')
        
    
for segmentData in results:
    if segmentData:
        ffmpeg_process.stdin.write(segmentData)
    
ffmpeg_process.stdin.close()
ffmpeg_process.wait()   
