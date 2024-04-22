# concurrent_painters
![canvas](https://github.com/hkomal01/concurrent_painters/assets/98800239/e364d84a-52db-4a52-a817-20196d79833c)
## Description:
Use multiple threads and some randomness to generate unique and colorful images
## Dependencies
Concurrent_painters relies on the following Python3 libraries
- Numpy
- Python Imaging Library (PIL)
## How to use
Run proceduaral_artist.py using a Python3 interpreter like so:
```console
python3 procerual_artist.py -M x -S y
```
There are two required flags:
1. -M
    - Determines the number of thread that will paint on the image at once
    - This is the number of different splotches in the image
3. -S
    - The number of steps to paints
    - In each step, every painter will attempt to paint a single pixel


