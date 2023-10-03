import requests
import m3u8
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import ffmpeg
import concurrent.futures

url = input('m3u8 URL to be downloaded: ')
output_filename = 'output.mp4'
user_agent = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}

def proccess_segment(segsurl, urlIndex):
    stream_encrypted = requests.get(segsurl.absolute_uri, headers=user_agent).content
    stream_decrypted = cipher.decrypt(stream_encrypted)
    stream_decrypted = unpad(stream_decrypted, AES.block_size)
    return urlIndex, stream_decrypted

ffmpeg_process = (
    ffmpeg.input('pipe:', format='mpegts')
    .output(output_filename, c='copy')
    .run_async(pipe_stdin=True, overwrite_output=True)
)

indexObject = m3u8.load(url)
segment_amount = len(indexObject.segments)
work_counter = 0
print(f'\n{segment_amount} segments to be downloaded.')

encryption_key = requests.get(indexObject.keys[0].absolute_uri, headers=user_agent).content
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
                print(f'Progress: {round(work_counter*100/segment_amount, 1)}%', end='\r')
            else:
                print(f'Progress: {round(work_counter*100/segment_amount, 1)}%\n')
        
    
for segmentData in results:
    if segmentData:
        ffmpeg_process.stdin.write(segmentData)
    
ffmpeg_process.stdin.close()
ffmpeg_process.wait()   
