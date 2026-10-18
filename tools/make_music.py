"""Generate an original, quiet instrumental loop from sine waves only."""
import math,struct,wave
from pathlib import Path
root=Path(__file__).resolve().parents[1];path=root/'video/music.wav';path.parent.mkdir(exist_ok=True)
rate=24000;seconds=16;notes=[261.6256,329.6276,391.9954,523.2511,220,261.6256,329.6276,440]
with wave.open(str(path),'wb') as stream:
 stream.setparams((1,2,rate,0,'NONE','not compressed'))
 data=bytearray()
 for i in range(rate*seconds):
  t=i/rate;beat=int(t/.5);phase=t% .5;f=notes[beat%len(notes)]
  env=min(1,phase/.025)*math.exp(-phase*6)*min(1,(seconds-t)/.5)
  value=.12*env*(math.sin(2*math.pi*f*t)+.22*math.sin(4*math.pi*f*t))
  data.extend(struct.pack('<h',round(value*32767)))
 stream.writeframes(data)
print(path)
