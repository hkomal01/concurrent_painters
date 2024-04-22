###
### procedural_artist.py
###
### Problem Set 4 - CS21 Concurrent Programming
### Harshdeep S. Komal (hkomal01)
### 
### Implements the procedural_artist functions from problem set 4.
###
###

import argparse
import sys
import numpy as np
import random
from threading import Thread
from threading import Lock
from threading import Barrier
from PIL import Image

# Locks for each of shared data structures b/w threads
pixel_lock  = Lock() # starting pixel list
color_lock  = Lock() # thread color list
canvas_lock = Lock() # shared canvas lock

def parseArgs():
    '''
    parseArgs
    Uses argparse to parse given arguments as well as error check
    
    Returns args tuple on success (int*int)
    On error, exits program with the following error codes:
        1 - Number of threads given is 0 or below
        2 - Number of steps given is below 0
        3 - Number of threads exceed 512*512 (pixels on canvas)
    '''
    # Begin adding all arguments to the parser
    parser = argparse.ArgumentParser(prog="transform_image.py")
    parser.add_argument('-M', help = "Number of threads to run",
                        required = True, type = int)
    parser.add_argument('-S', help = "Number of steps of simulation to run",
                        required = True, type = int)
    args = parser.parse_args()
    # Check that threads isn't 0 or below
    if args.M <= 0:
        print("ERROR: Number of threads cannot be nonpositive.",
              file = sys.stderr)
        sys.exit(1) # Exit code 1
    # 0 or more steps given
    elif args.S < 0:
        print("ERROR: Cannot run a negative number of simulation steps.",
              file = sys.stderr)
        sys.exit(2) # Exit code 2
    elif args.M > 512**2:
        print("ERROR: More threads than number of pixels in canvas.",
              file = sys.stderr)
        sys.exit(3) # Exit code 3
    
    return (args.M, args.S) 

def constrain(x, mn, mx):
    '''
    constrain
    Constrains the value x between mx and mx inclusive so that mn <= x <= mx
    
    x : Number to constrain (num)
    mn: The lower bound to constrain x with or the min (num)
    mx: The upper bound to constrain x with or the max (num)

    Returns either x, mn, or mx (num)
    '''
    return max(min(x, mx), mn) 

def get_rgb(img, x, y):
    '''
    get_rgb
    Wrapper for img.getpixel so that RGBA/RGB both work

    img: The image to extract a pixel from (PIL Image Object)
    x  : The x-coordinate of the pixel (int)
    y  : The y-coordinate of the pixel (int)

    Returns the pixel extracted (int*int*int)
    '''
    return img.getpixel((x, y))[0:3]

def colorPicker(colors):
    '''
    colorPicker
    Generates a unique color (256^3 max) in a thread-safe way

    colors: List of colors in use (int*int*int list)

    Returns a random color from as a RGB tuple (int*int*int)

    Note:
    Colors is modified BY REFERENCE as a side effect
    '''
    # Variances which determine how far from red, green, blue each color is
    var  = 50  # Variance for non-primary bands
    var2 = 150 # Variance for primary band
    # I use a normal distribution so the colors are somewhat close to RGB
    red   = (np.random.normal(200, var), # Primary band 
             np.random.normal(0, var2), 
             np.random.normal(0, var2))
    # Constrain the value just in case its above x < 0 or x > 255
    red = [int(constrain(x, 0, 255)) for x in red]
    green = (np.random.normal(0, var2), 
             np.random.normal(200, var), # Primary band
             np.random.normal(0, var2))
    green = [int(constrain(x, 0, 255)) for x in green]
    blue  = (np.random.normal(0, var2), 
             np.random.normal(0, var2), 
             np.random.normal(200, var)) # Primary band
    blue = [int(constrain(x, 0, 255)) for x in blue]

    # RGB tuple creation sample one of those three random colors
    x = tuple(random.sample([red, blue, green], 3)[0])
    # Double check this color isn't already taken and isn't white just in case
    if x not in colors and not x == (255, 255, 255):
        with color_lock:
            colors.append(x)
        return x
    # Else collision, so recursively recall function until we find unique color
    return colorPicker(colors)

def pixelPicker(held):
    '''
    pixelPicker
    Generates a unique pixel (512^2 max) in a thread-safe way

    held: List of starting pixels in use (int*int list)

    Returns a random pxel from as a (x,y) tuple (int*int)

    Note:
    Colors is modified BY REFERENCE as a side effect
    '''
    # Pick a random integer in [0, 511]
    (x, y) = (random.randint(0, 511), random.randint(0, 511))
    # If this pixel isn't someone else's starting value
    if (x, y) not in held:
        # Place it before it gets 'stolen'
        with pixel_lock:
            held.append((x, y))
        return (x, y)
    # Else random starting pixel is already 'held' by another thread
    return pixelPicker(held)

def paint_t(held, colors, img, steps, barrier):
    '''
    paint_t
    Function that each thread calls to paint their pixels

    held   : Shared data structure between threads which stores starting pixels
             (int*int list)
    colors : Shared data structure between threads which stores thread colors
             (int*int*int list)
    img    : Shared canvas on which all threads paint (PIL Image Object)
    steps  : Number of steps each thread paints for (int)
    barrier: Barrier to signal all threads to begin painting beyond first pixel
             (Python Barrier Object)

    Returns nothing but modifies the shared canvas (PIL Image Object)
    '''
    # Pick a color for the thread
    color = colorPicker(colors)
    # Pick the starting pixel for the thread AND also make sure no one 
    # 'steals' the pixel selection before it's placed
    with canvas_lock: 
        # Select a random pixel
        (x, y) = pixelPicker(held)
        # Keep reselecting if pixel isn't white somehow
        while get_rgb(img, x, y) != (255, 255, 255):
            (x, y) = pixelPicker(held)
        img.putpixel((x, y), color)
    # Initialize stack with starting pixel
    stack = [(x, y)]
    width  = img.size[0]
    height = img.size[1]
    # This lambda checks to see where a given pixel is both in bounds
    # and that the space is uncolored
    valid = lambda a, b: (0 <= a < width) and (0 <= b < height)\
                    and  (get_rgb(img, a, b) == (255, 255, 255))
    # Wait for all threads to choose their starting pixel
    barrier.wait()
    # Once All threads have picked a starting pixels, begin painting
    while stack != [] and steps > 1:
        (x, y) = stack[-1] # Peek stack
        steps = steps - 1
        moves = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        # Check for valid_moves with lock so no other thread 'steals' the spot
        canvas_lock.acquire()
        moves = [(a, b) for (a, b) in moves if valid(a, b)]
        # If no valid moves, pop and try from *random* pixel
        if (len(moves) == 0):
            canvas_lock.release()
            stack.pop()
            np.random.shuffle(stack)
            continue
        # Randomly choose the move from valid choices and place it
        move = random.sample(moves, 1)[0]
        img.putpixel(move, color)
        canvas_lock.release() # Release lock
        stack.append(move) # Push new pixel

def paint(canvas, num_threads, num_steps):
    '''
    paint
    Start up each thread to begin painting and then joins them

    canvas     : Blank shared canvas for threads to paint on (PIL Image Object)
    num_threads: Number of threads to run (int)
    num_steps  : Number of steps of the simulation to run (int)

    Returns nothing but modified the shared canvas (PIL Image Object)
    '''
    threads = []
    held    = []
    colors  = []
    # No need to perform computations if no steps in painting
    if (num_steps == 0):
        return
    # Initialize barrier to signal all threads to continue painting
    barrier = Barrier(num_threads)

    # For each thread, run paint_t to begin painting
    for _ in range(num_threads):
        thread = Thread(target = paint_t, 
                        args = (held, colors, canvas, num_steps, barrier))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def main():
    (num_threads, num_steps) = parseArgs()

    # Initialize a 512x512 white canvas in RGB mode
    canvas = Image.new('RGB', (512, 512), color = (255, 255, 255))
    # Paint the canvas with the number of threads and steps
    paint(canvas, num_threads, num_steps)
    # Save painted canvas as a jpg
    canvas.save('canvas.png')

    return 0

if __name__ == "__main__":
    main()
