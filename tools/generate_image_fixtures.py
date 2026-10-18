"""Creates synthetic, non-personal fixtures in a requested NEW output directory."""
import argparse, io, struct, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageCms, PngImagePlugin, TiffImagePlugin

def chunk(kind,payload): return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
def generate(path):
 path=Path(path);path.mkdir(parents=True,exist_ok=False);w,h=160,96;y,x=np.mgrid[:h,:w];rgb=np.stack([x*255//(w-1),y*255//(h-1),(x+y)*255//(w+h-2)],-1).astype(np.uint8);im=Image.fromarray(rgb);icc=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
 for orientation in [1,6]:
  ex=Image.Exif();ex[274]=orientation;ex[315]='Synthetic fixture';ex[34853]={1:'N',2:(TiffImagePlugin.IFDRational(31),TiffImagePlugin.IFDRational(12),TiffImagePlugin.IFDRational(0)),3:'E',4:(TiffImagePlugin.IFDRational(121),TiffImagePlugin.IFDRational(30),TiffImagePlugin.IFDRational(0))};buf=io.BytesIO();im.save(buf,format='JPEG',quality=95,exif=ex,icc_profile=icc);data=buf.getvalue();segments=[]
  for marker,payload in [(b'\xff\xe1',b'http://ns.adobe.com/xap/1.0/\0<synthetic/>'),(b'\xff\xed',b'Photoshop 3.0\0'+b'8BIM'+b'\x04\x04'+b'\x00\x00'+struct.pack('>I',14)+b'\x1c\x02\x78\x00\x09Synthetic'),(b'\xff\xfe',b'Synthetic comment')]: segments.append(marker+struct.pack('>H',len(payload)+2)+payload)
  (path/f'orientation{orientation}.jpg').write_bytes(data[:2]+b''.join(segments)+data[2:])
 meta=PngImagePlugin.PngInfo();meta.add_text('Author','Synthetic');meta.add_text('Compressed','Synthetic text',zip=True);meta.add_itxt('International','合成样本');ex=Image.Exif();ex[315]='Synthetic'
 for name,image in [('rgb.png',im),('rgba.png',Image.fromarray(np.dstack([rgb,(x*255//(w-1)).astype(np.uint8)]))),('gray.png',im.convert('L')),('palette.png',im.convert('P'))]: image.save(path/name,pnginfo=meta,icc_profile=icc,dpi=(96,96),exif=ex)
 (path/'bad.png').write_bytes(b'not an image')
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(generate(a.output))
