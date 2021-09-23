import io

from pydub import AudioSegment
from shazamio import Shazam

from common import de_async

def shazam_recognize(data):
    return de_async(shazam_recognize_async, data)


async def shazam_recognize_async(data):
    shazam = Shazam()

    return await shazam.recognize_song_from_bytes(data)

# for some reason, shazam doesnt have recognize_from_bytes_data
async def recognize_from_bytes_data(self, data):
    audio = AudioSegment.from_file(io.BytesIO(data))
    audio = audio.set_sample_width(2)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)

    signature_generator = self.create_signature_generator(audio)
    signature = signature_generator.get_next_signature()
    while not signature:
        signature = signature_generator.get_next_signature()

    return await self.send_recognize_request(signature)
Shazam.recognize_song_from_bytes = recognize_from_bytes_data

