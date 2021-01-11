from future.builtins import map
import png

from django.http import HttpResponse
from djpyfs import djpyfs

arrow = ["11011",
         "10001", 
         "00000", 
         "11011", 
         "11011", 
         "11011", 
         "10001"]
arrow = [list(map(int, x)) for x in arrow]


def index(_):
    fs = djpyfs.get_filesystem("sample")
    f = fs.open("uparrow.png", "wb")
    png.Writer(len(arrow[0]), len(arrow), greyscale=True, bitdepth=1).write(f, arrow)
    f.close()

    url = fs.get_url("uparrow.png")

    return HttpResponse(
        f"<html><body>Hello, world. You're at the test index. <img src=\"{url}\"> </body></html>"
    )
