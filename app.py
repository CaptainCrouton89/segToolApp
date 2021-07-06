from pathlib import Path
from PIL import Image, ImageTk
from warpTools import four_point_transform, order_points
import math
import cornerDetectionTools
from rotationTools import smart_rotate
from cvTools import *
from tkinter import filedialog, Canvas, Frame
from tkinter import ttk, Tk, BOTH, N, S, E, W, LEFT, TOP, BOTTOM, CURRENT, NW, NE, SW, SE, END
import os
import cv2
import numpy as np
import argparse

CW = 90
CCW = -90

default_image = "assets/default_img.png"


def recursive_map(f, it):
    return (recursive_map(f, x) if isinstance(x, tuple) else f(x) for x in it)


class App():

    def __init__(self, name, verbosity=0, in_folder=None):
        self.default_in_folder = in_folder

        self.verbosity = verbosity

        

        self.root = self.draw_window(name)
        self.style = ttk.Style()
        self.style.configure("BW.TLabel", foreground="black", background="white")

        self.root.bind('<Return>', self.set_dims)
        self.root.bind('<r>', self.recalculate_corners)
        self.root.bind('<f>', self._next_frame)
        self.root.bind('<n>', self._next_frame)
        self.root.bind('<Right>', self._next_frame)
        self.root.bind('<d>', self._prev_frame)
        self.root.bind('<p>', self._prev_frame)
        self.root.bind('<Left>', self._prev_frame)

        self.root.bind('<b>', self.load_images)

    def run(self):
        self.root.mainloop()
        self.refresh()

    def draw_window(self, name):
        root = Tk(name)
        
        self.all_images = []

        self.style = ttk.Style()
        self.style.configure("BW.TLabel", foreground="black", background="white")

        content = ttk.Frame(master=root, padding=(3,3,3,3), borderwidth=5, relief="ridge")
        content.pack(fill=BOTH, expand=1)

        content.rowconfigure([0, 1, 2], minsize=50)
        content.columnconfigure([0], minsize=50)
        content.rowconfigure(1, weight=0)
        content.rowconfigure(2, weight=4)
        content.columnconfigure(0, weight=1)

        header = self._draw_header(content)
        header.grid(row=0, column=0, sticky=(N, S, E, W))

        navbar = self._draw_nav(content)
        navbar.grid(row=1, column=0, sticky=(N, S, E, W))

        editor_frame = self._draw_editor(content)
        editor_frame.grid(row=2, column=0, sticky=(N, S, E, W))
        return root

    def _draw_header(self, content):
        header = ttk.Frame(master=content, padding=(3,3,3,3), width=600, height=50, borderwidth=5, relief="ridge")
        self.name = ttk.Label(master=header, text="NAME", style="BW.TLabel")
        self.name.pack()
        return header

    def _draw_nav(self, content):
        navbar = ttk.Frame(master=content, padding=(3,3,3,3), width=600, height=10, borderwidth=5, relief="ridge")

        navbar.columnconfigure([0, 5], minsize=50)
        navbar.rowconfigure(0, weight=1)

        navbar.columnconfigure(0, weight=1)
        navbar.columnconfigure(1, weight=1)
        navbar.columnconfigure(2, weight=1)
        navbar.columnconfigure(3, weight=1)
        navbar.columnconfigure(4, weight=1)
        navbar.columnconfigure(5, weight=1)


        bt_next = ttk.Button(navbar, text="NEXT", command=self._next_frame)
        bt_next.grid(row=0, column=5, rowspan=2, sticky=(N, S, E, W))

        bt_prev = ttk.Button(navbar, text="PREVIOUS", command=self._prev_frame)
        bt_prev.grid(row=0, column=0, rowspan=2, sticky=(N, S, E, W))

        bt_browse = ttk.Button(navbar,text="Browse",command=self.load_images, takefocus=False)
        bt_browse.grid(row=0, column=2, columnspan=2, sticky=(N, S, E, W))
        return navbar

    def _draw_editor(self, content):
        editor_frame = ttk.Frame(master=content, padding=(3,3,3,3), width=600, height=5, borderwidth=5, relief="ridge")

        editor_frame.rowconfigure(1, weight=1)

        editor_frame.columnconfigure(0, weight=1)
        editor_frame.columnconfigure(1, weight=1)

        self.editor_frame = editor_frame

        controls_frame = ttk.Frame(master=editor_frame)
        controls_frame.grid(row=0, column=0, columnspan=2)

        entry_frame = ttk.Frame(master=controls_frame)
        entry_frame.grid(row=0, column=0)

        self.pv_width = ttk.Entry(master=entry_frame)
        self.pv_height = ttk.Entry(master=entry_frame)
        self.bt_setdim = ttk.Button(master=entry_frame, text="Set", command=self.set_dims)
        self.pv_width.insert(END, 10)
        self.pv_height.insert(END, 6)
        self.pv_width.pack(side=LEFT)
        self.pv_height.pack(side=LEFT)
        self.bt_setdim.pack(side=LEFT)

        bt_recal_corners = ttk.Button(entry_frame, text="Recalculate",command=self.recalculate_corners)
        bt_recal_corners.pack(side=LEFT)

        self.draw_image_frames(editor_frame)
        return editor_frame

    def draw_image_frames(self, editor_frame):
        self.persp_frame = Frame(editor_frame, width=100, height=100, borderwidth=5, relief="ridge")
        self.persp_frame.grid(row=1, column=0, sticky="nsew")
        self.seg_frame = Frame(editor_frame, width=100, height=100, borderwidth=5, relief="ridge")
        self.seg_frame.grid(row=1, column=1, sticky="nsew")
        
        padx = 2
        pady = 2
        
        self.persp_image = PerspectiveView(self, self.persp_frame)
        self.persp_image.canvas.pack(side=LEFT, fill="both", expand=True, padx=padx, pady=pady)

        self.seg_image = SegmentView(self, self.seg_frame)
        self.seg_image.canvas.pack(side=LEFT, fill="both", expand=True, padx=padx, pady=pady)

    def load_images(self, event=None):
        w, h = self.persp_frame.winfo_width(), self.persp_frame.winfo_height()
        self.all_images = []
        self.index = -1

        if not self.default_in_folder:
            folder = filedialog.askdirectory(initialdir=".")
        else:
            folder = self.default_in_folder
        in_path = Path(folder)
        for filename in os.listdir(folder):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                filepath = str(in_path / filename)
                self.all_images.append(ImageLoad(filepath, resize=(w-10, h-10), verbosity=self.verbosity))
        print([i.path for i in self.all_images])
        
        self._next_frame()

    def save_to(self):
        folder = filedialog.askdirectory(initialdir=".")

    def _next_frame(self, event=None):
        
        if self.verbosity > 2:
            print("next")
        if not self.all_images:
            return
        self.index += 1
        if self.index >= len(self.all_images):
            self.index = 0
        self._change_frame()

    def _prev_frame(self, event=None):
        if self.verbosity > 2:
            print("back")
        if not self.all_images:
            return
        self.index -= 1
        if self.index < 0:
            self.index = len(self.all_images)-1
        self._change_frame()

    def _change_frame(self):
        image_load = self.all_images[self.index]

        self.persp_image.set_image(image_load)
        self.seg_image.set_image(image_load)

        self.name.config(text=self.persp_image.image_load.path)

        self.refresh()


    def refresh(self):
        self.persp_image.clear_all()
        self.seg_image.clear_all()
        self.seg_image.image_load.refresh()
        self.persp_image.refresh()
        self.seg_image.refresh()

        # if not self.seg_image.image_load.refresh():
        #     self._next_frame()
        # else:
        #     self.persp_image.refresh()
        #     self.seg_image.refresh()

    def set_dims(self, event=None):
        self.persp_image.image_load.x_cells = int(self.pv_width.get())
        self.persp_image.image_load.y_cells = int(self.pv_height.get())
        if self.verbosity > 1:
            print("width:", self.pv_width.get(), "\nheight:", self.pv_height.get())

        # Testing
        # self.seg_image.image_load.calculate_lines()
        self.refresh()


    def recalculate_corners(self, event=None):
        self.persp_image.clear_all()
        self.persp_image.image_load.auto_detect()
        self.refresh()

class ImageLoad():

    def __init__(self, path, resize, verbosity=0):
        self.skip = False

        self.verbosity = verbosity
        self.resize = resize

        self.x_cells = 10
        self.y_cells = 6

        self.path = path
        self.cv_image = cv2.imread(path)
        self.o_pil_image = Image.open(path)
        self.pil_image = self.o_pil_image.resize((resize[0], resize[1]))
        self.tk_image = ImageTk.PhotoImage(self.pil_image)

        self.cv_warp_image = None
        self.cv_rotation_image = None
        self.pil_transform_image = None
        self.tk_transform_image = None
        self.width, self.height = self.o_pil_image.size

        # Persp shift vars
        self.resize_factor = (resize[0]/self.width, resize[1]/self.height)
        if (self.verbosity > 1):
            print("resize:", resize)
            print("resize factor:", self.resize_factor)

        self.transform = []
        self.rotation = None
    
        self.transform_resize_factor = None

        self.corners = np.array([])
        self.adjusted_corners = np.array([])

        # Overlay lines on cv_warp
        self.vert_lines = []
        self.hor_lines = []

    def calculate_lines(self):
        self.vert_lines = []
        self.hor_lines = []
        # uses adjustad corners to calculate intermediaries
        height, width, _ = self.cv_warp_image.shape
        ordered_pts = [
            [0, 0],
            [width, 0],
            [width, height],
            [0, height]
        ]
        offset_pts = ordered_pts[1:]
        offset_pts.append(ordered_pts[:1][0])
        for i, (pt1, pt2) in enumerate(zip(offset_pts, ordered_pts)):
            if i % 2 == 0:
                self.vert_lines.append(get_midpoints(pt1, pt2, self.x_cells))
            else:
                self.hor_lines.append(get_midpoints(pt1, pt2, self.y_cells))

    def auto_detect(self):
        if self.verbosity > 1:
            print("auto-detecting corners")
        self.corners = cornerDetectionTools.find_corners(self.cv_image)
        self.adjusted_corners = self.convert_points_forward(*self.corners)

    def refresh(self):
        global default_image
        # If points never set yet, will auto-calculate best guess
        if self.corners.shape[0] == 0 and self.adjusted_corners.shape[0] == 0:
            self.auto_detect()
        
        if self.adjusted_corners.shape[0] != 0:
            if self.verbosity > 1:
                print("loading corners from save")
            self.corners = self.convert_backward(*self.adjusted_corners)
            # self.adjusted_corners = self.convert_points_forward(*self.corners)

        if self.verbosity > 1:
            print("adjusted corners:", self.adjusted_corners)
            print("corners to warp on:", self.corners)

        if self.corners.shape[0] != 4:
            if self.verbosity > 0:
                print("Bad Image")
            self.skip = True
            seg_img = cv2.imread(default_image)
        else:
            self.skip = False
            self.cv_warp_image, self.trans_matrix = four_point_transform(self.cv_image, self.corners)
            self.calculate_lines()
            self.untransform_lines()
            seg_img = self.cv_warp_image.copy()
            persp_img = self.cv_image.copy()

            # Adding lines to seg_img
            self.apply_grid(seg_img, self.vert_lines[0], reversed(self.vert_lines[1]))
            self.apply_grid(seg_img, self.hor_lines[0], reversed(self.hor_lines[1]))
            # Adding lines to persp_img
            self.apply_grid(persp_img, self.warp_vert_lines[0], reversed(self.warp_vert_lines[1]))
            self.apply_grid(persp_img, self.warp_hor_lines[0], reversed(self.warp_hor_lines[1]))

        # Converting seg_img
        seg_img = cv2.cvtColor(seg_img, cv2.COLOR_BGR2RGB)
        seg_img = Image.fromarray(seg_img)
        self.pil_transform_image = seg_img.resize(self.resize)
        self.tk_transform_image = ImageTk.PhotoImage(self.pil_transform_image)
        # Converting persp_img
        persp_img = cv2.cvtColor(persp_img, cv2.COLOR_BGR2RGB)
        persp_img = Image.fromarray(persp_img)
        self.pil_image = persp_img.resize(self.resize)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        print(self.tk_image)
        return True

    def untransform_lines(self):
        # Test code—this works. The output has chopped off everything outside the transform
        # inv_trans = np.linalg.pinv(self.trans_matrix)
        # round_tripped = cv2.warpPerspective(self.cv_warp_image, inv_trans, (self.width, self.height))
        # show(round_tripped)
        inv_trans = np.linalg.pinv(self.trans_matrix)
        self.warp_vert_lines = []
        self.warp_hor_lines = []
        for line in self.vert_lines:
            self.warp_vert_lines.append([self.transform_point(p, inv_trans) for p in line])
        for line in self.hor_lines:
            self.warp_hor_lines.append([self.transform_point(p, inv_trans) for p in line])

    def transform_point(self, p, matrix):
        px = (matrix[0][0]*p[0] + matrix[0][1]*p[1] + matrix[0][2]) / ((matrix[2][0]*p[0] + matrix[2][1]*p[1] + matrix[2][2]))
        py = (matrix[1][0]*p[0] + matrix[1][1]*p[1] + matrix[1][2]) / ((matrix[2][0]*p[0] + matrix[2][1]*p[1] + matrix[2][2]))
        return (int(px), int(py))

    def apply_grid(self, img, lines1, lines2):
        for pt1, pt2 in zip(lines1, lines2):
            cv2.line(img, pt1, pt2, color=(255, 255, 255), thickness=5)

    def convert_points_forward(self, *points):
        output = []
        for p in points:
            px, py = p[0]*self.resize_factor[0], p[1]*self.resize_factor[1]
            output.append([px, py])
        return np.array(output)

    def convert_backward(self, *points):
        output = []
        for p in points:
            px, py = int(p[0]/self.resize_factor[0]), int(p[1]/self.resize_factor[1])
            output.append([px, py])
        return np.array(output)
   

class InteractiveCanvas():

    radius = 3

    def __init__(self, app, master, verbosity=0):
        self.app = app

        self.selected = None

        self.canvas = Canvas(master, width=500, height=500)
        self.image = self.canvas.create_image(0, 0, anchor = NW, image=None)

        self.canvas.bind('<1>', self.select_circle)
        self.canvas.bind('<Shift-1>', self.make_circle)
        self.canvas.bind('<Control-1>', self.delete_circle)

        self.indicators = []

    def make_circle(self, event):
        x, y, r = event.x, event.y, self.radius
        self.indicators.append(self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', fill='white'))

    def delete_circle(self, event):
        x, y, r = event.x, event.y, self.radius

    def clear_all(self):
        for point in self.indicators:
            self.canvas.delete(point)

    def set_image(self, image_load):
        self.image_load = image_load

    def select_circle(self, event):
        self.canvas.bind('<Motion>', self.move_circle)
        self.canvas.bind('<ButtonRelease-1>', self.deselect)

        self.canvas.addtag_withtag('selected', CURRENT)

    def move_circle(self, event):
        x, y, r = event.x, event.y, self.radius
        self.canvas.coords('selected', x-r, y-r, x+r, y+r)

    def deselect(self, event):
        self.canvas.dtag('selected')    # removes the 'selected' tag
        self.canvas.unbind('<Motion>')
        self.canvas.bind('<Shift-1>', self.make_circle)


class PerspectiveView(InteractiveCanvas):
    def __init__(self, master, verbosity=0):
        super().__init__(master, verbosity)

    # def draw_midpoints(self):
    #     r = self.radius
    #     for i, line_list in enumerate(self.image_load.line_lists):
    #         for p in line_list:
    #             print(p)
    #             x, y = int(p[0]), int(p[1])
    #             self.indicators.append(self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', fill='blue'))

    def draw_points(self, *points):
        self.indicators = []
        r = self.radius
        for p in points:
            x, y = int(p[0]), int(p[1])
            self.indicators.append(self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', fill='white'))

    def update_corners(self):
        if self.indicators:
            corners = []
            for widget in self.indicators:
                x1, y1, _, _ = self.canvas.coords(widget)
                corners.append([x1+self.radius, y1+self.radius])
            self.image_load.adjusted_corners = np.asarray(corners)
            self.image_load.refresh()
            self.app.refresh()

    def deselect(self, event):
        super().deselect(event)
        self.update_corners()

    def delete_circle(self, event):
        super().delete_circle(event)
        self.update_corners()

    def make_circle(self, event):
        super().make_circle(event)
        self.update_corners()

    def refresh(self):
        self.canvas.itemconfig(self.image, image = self.image_load.tk_image)
        self.draw_points(*self.image_load.adjusted_corners)


class SegmentView(InteractiveCanvas):
    def __init__(self, master, verbosity=0):
        super().__init__(master, verbosity)

    def refresh(self):
        self.canvas.itemconfig(self.image, image=self.image_load.tk_transform_image)

    def clear_all(self):
        pass

    def rotate(self, direction):
        pass


def get_midpoints(pt1, pt2, splits):
    midpoints = []
    x1, y1 = pt1[0], pt1[1]
    x2, y2 = pt2[0], pt2[1]
    for i in range(splits+1):
        d = i/splits #0/10, 1/10, ..., 10/10
        x = x1+(d*(x2-x1))
        y = y1+(d*(y2-y1))
        midpoints.append((int(x), int(y)))
    return midpoints

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbosity", action="count", default=0, help="Print intermediary steps")
    ap.add_argument("-i", "--in_path", default=None, help="Print intermediary steps")
    args = ap.parse_args()

    app = App("Segmentation Tools", verbosity=args.verbosity, in_folder=args.in_path)
    app.run()
    

if __name__ == '__main__':
    main()