from pathlib import Path
from datetime import date
import json
from shapely.geometry import Polygon
from PIL import Image, ImageTk
from warpTools import four_point_transform, order_points
import math
import cornerDetectionTools
from rotationTools import smart_rotate
from cvTools import *
from tkinter import filedialog, Canvas, Frame
from tkinter.messagebox import showinfo
import tkinter as tk
import os
import cv2
import numpy as np
import argparse
import cocoConfig

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
        self.root.bind('<Return>', self.set_dims)
        self.root.bind('<c>', self.set_dims)
        self.root.bind('<w>', self.switch_dims)
        self.root.bind('<Command-r>', self.recalculate_corners)
        self.root.bind('<f>', self._next_frame)
        self.root.bind('<n>', self._next_frame)
        self.root.bind('<Right>', self._next_frame)
        self.root.bind('<d>', self._prev_frame)
        self.root.bind('<p>', self._prev_frame)
        self.root.bind('<Left>', self._prev_frame)
        self.root.bind('<Command-b>', self.load_images)
        self.root.bind('<Command-s>', self.save_to)
        self.root.bind('<Shift-s>', self.skip)

    def run(self):
        self.root.mainloop()
        self.refresh()

    def draw_window(self, name):
        root = tk.Tk(name)
        root.title("SolarPanelSegmentater-3000")
        
        self.all_images = []

        content = tk.Frame(master=root, padx=3, pady=3, borderwidth=5, relief="ridge")
        content.pack(fill=tk.BOTH, expand=1)

        content.rowconfigure([0, 1, 2], minsize=50)
        content.columnconfigure([0], minsize=50)
        content.rowconfigure(1, weight=0)
        content.rowconfigure(2, weight=4)
        content.columnconfigure(0, weight=1)

        header = self._draw_header(content)
        header.grid(row=0, column=0, sticky=("nsew"))

        navbar = self._draw_nav(content)
        navbar.grid(row=1, column=0, sticky=("nsew"))

        editor_frame = self._draw_editor(content)
        editor_frame.grid(row=2, column=0, sticky=("nsew"))
        return root

    def _draw_header(self, content):
        header = tk.Frame(master=content, padx=3, pady=3, width=600, height=50, borderwidth=5, relief="ridge")
        self.name = tk.Label(master=header, text="NAME", fg="black")
        keybinds = tk.Label(master=header, text="All buttons are bound to the key corresponding to their first capital letter.", fg="black")
        guide = tk.Label(master=header, text="Shift-Click to add point.", fg="black")
        self.name.pack()
        keybinds.pack()
        guide.pack()
        return header

    def _draw_nav(self, content):
        navbar = tk.Frame(master=content, padx=3, pady=3, width=600, height=10, borderwidth=5, relief="ridge")

        navbar.columnconfigure([0, 5], minsize=50)
        navbar.rowconfigure(0, weight=1)

        navbar.columnconfigure(0, weight=1)
        navbar.columnconfigure(1, weight=1)
        navbar.columnconfigure(2, weight=1)
        navbar.columnconfigure(3, weight=1)
        navbar.columnconfigure(4, weight=1)
        navbar.columnconfigure(5, weight=1)


        bt_next = tk.Button(navbar, text="Next", command=self._next_frame, fg="black")
        bt_next.grid(row=0, column=5, rowspan=2, sticky=("nsew"))

        bt_prev = tk.Button(navbar, text="Previous", command=self._prev_frame, fg="black")
        bt_prev.grid(row=0, column=0, rowspan=2, sticky=("nsew"))

        bt_browse = tk.Button(navbar,text="Browse",command=self.load_images, fg="black")
        bt_browse.grid(row=0, column=2, columnspan=2, sticky=("nsew"))
        return navbar

    def _draw_editor(self, content):
        editor_frame = tk.Frame(master=content, padx=3, pady=3, width=600, height=5, borderwidth=5, relief="ridge")
        self.editor_frame = editor_frame

        controls_frame = tk.Frame(master=editor_frame)
        controls_frame.pack(side=tk.TOP, fill="x")

        self.pv_width = tk.Entry(master=controls_frame, width=3, fg="black", bg="white")
        self.pv_height = tk.Entry(master=controls_frame, width=3, fg="black", bg="white")
        self.bt_setdim = tk.Button(master=controls_frame, text="Confirm dimensions", command=self.set_dims, fg="black")
        self.bt_switchdim = tk.Button(master=controls_frame, text="sWitch dimensions", command=self.switch_dims, fg="black")
        bt_recal_corners = tk.Button(controls_frame, text="Recalculate",command=self.recalculate_corners, fg="black")
        bt_save = tk.Button(controls_frame, text="Save",command=self.save_to, fg="black")

        self.pv_width.insert(tk.END, 10)
        self.pv_height.insert(tk.END, 6)

        self.pv_width.pack(side=tk.LEFT)
        self.pv_height.pack(side=tk.LEFT)
        self.bt_setdim.pack(side=tk.LEFT)
        self.bt_switchdim.pack(side=tk.LEFT)
        bt_recal_corners.pack(side=tk.LEFT)
        bt_save.pack(side=tk.LEFT)

        self.draw_image_frames(editor_frame)
        return editor_frame

    def draw_image_frames(self, editor_frame):
        self.persp_frame = Frame(editor_frame, width=100, height=100)
        self.persp_frame.pack(side=tk.TOP, fill="both", expand=True)

        self.persp_image = PerspectiveView(self, self.persp_frame)
        self.persp_image.canvas.pack(side=tk.LEFT, fill="both", expand=True, padx=2, pady=2)

    def load_images(self, event=None):
        w, h = self.persp_frame.winfo_width(), self.persp_frame.winfo_height()
        self.all_images = []
        self.index = -1

        if not self.default_in_folder:
            self.folder = filedialog.askdirectory(initialdir=".")
        else:
            self.folder = self.default_in_folder
        in_path = Path(self.folder)
        for filename in os.listdir(self.folder):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                filepath = str(in_path / filename)
                self.all_images.append(ImageLoad(filepath, resize=(w-10, h-10), verbosity=self.verbosity))
        if self.verbosity > 0:
            for i in self.all_images:
                print(i.path)
        
        self._next_frame()

    def save_to(self, event=None):
        # folder = filedialog.askdirectory(initialdir=".")
        coco = cocoConfig.get_boiler()
        datetime = str(date.today())
        
        id = 0
        an_id = 0
        for image_load in self.all_images:
            if image_load.skip == False:
                id += 1
                coco["images"].append(
                    {
                        "id": id,
                        "width": image_load.width,
                        "height": image_load.height,
                        "file_name": image_load.path,
                        "license": coco["licenses"]["id"],
                        "flickr_url": "",
                        "coco_url": "",
                        "date_captured": datetime,
                    }
                )
                all_segmentations = image_load.get_bb()
                for segmentation in all_segmentations:
                    an_id += 1
                    polygon = Polygon(segmentation)
                    bbox = bounding_box(segmentation)
                    coco["annotations"].append(
                    {
                        "id": an_id,
                        "image_id": id,
                        "category_id": coco["categories"][0]["id"],
                        "segmentation": [[item for items in segmentation for item in items]],
                        "area": polygon.area,
                        "bbox": [bbox[0][0],bbox[0][0],bbox[1][0]-bbox[0][0],bbox[1][1]-bbox[0][1]],
                        "iscrowd": 0
                    }
                )
        path = str(Path(self.folder) / "annotations.json")
        f = open(path, "w+")
        json.dump(coco, f)

    def _next_frame(self, event=None):
        
        if self.verbosity > 2:
            print("next")
        if not self.all_images:
            return
        self.index += 1
        if self.index >= len(self.all_images):
            showinfo("End of folder", "You have reviewed all images in this folder. You may continue editing, or you may save and quit.")
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
        self.name.config(text=self.persp_image.image_load.path)
        self.refresh()

    def refresh(self):
        self.persp_image.clear_all()
        self.persp_image.image_load.refresh()
        self.persp_image.refresh()

    def skip(self, event=None):
        self.persp_image.image_load.skip = True
        self._next_frame()

    def set_dims(self, event=None):
        self.persp_image.image_load.x_cells = int(self.pv_width.get())
        self.persp_image.image_load.y_cells = int(self.pv_height.get())
        if self.verbosity > 1:
            print("width:", self.pv_width.get(), "\nheight:", self.pv_height.get())
        self.refresh()

    def switch_dims(self, event=None):
        h = int(self.pv_height.get())
        w = int(self.pv_width.get())
        self.pv_width.delete(0, tk.END)
        self.pv_height.delete(0, tk.END)
        self.pv_width.insert(tk.END, h)
        self.pv_height.insert(tk.END, w)
        self.set_dims()

    def recalculate_corners(self, event=None):
        self.persp_image.clear_all()
        self.persp_image.image_load.auto_detect()
        self.refresh()


class Segmentation():

    def __init__(self):
        self.x_cells = 10
        self.y_cells = 6
        self.corners = np.array([])
        self.adjusted_corners = np.array([])
        self.vert_lines = []
        self.hor_lines = []


class ImageLoad():

    def __init__(self, path, resize, verbosity=0):
        self.skip = True

        self.verbosity = verbosity
        self.resize = resize

        # Should be multiple
        self.x_cells = 6
        self.y_cells = 10

        self.path = path
        self.cv_image = cv2.imread(path)
        self.o_pil_image = Image.open(path)
        self.pil_image = self.o_pil_image.resize((resize[0], resize[1]))
        self.tk_image = ImageTk.PhotoImage(self.pil_image)

        self.cv_warp_image = None

        self.width, self.height = self.o_pil_image.size

        # Persp shift vars
        self.resize_factor = (resize[0]/self.width, resize[1]/self.height)
        if (self.verbosity > 1):
            print("resize:", resize)
            print("resize factor:", self.resize_factor)
    
        self.transform_resize_factor = None

        self.segmentations = [Segmentation(), Segmentation()]

    def calculate_lines(self, img, segmentation):
        vert_lines = []
        hor_lines = []
        # uses adjustad corners to calculate intermediaries
        height, width, _ = img.shape
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
                vert_lines.append(get_midpoints(pt1, pt2, segmentation.x_cells))
            else:
                hor_lines.append(get_midpoints(pt1, pt2, segmentation.y_cells))

        return vert_lines, hor_lines

    def auto_detect(self):
        if self.verbosity > 1:
            print("auto-detecting corners")
        corners = cornerDetectionTools.find_corners(self.cv_image)
        adjusted_corners = self.convert_points_forward(*corners)
        return corners, adjusted_corners

    def refresh(self):
        global default_image
        # If points never set yet, will auto-calculate best guess
        seg = self.segmentations[0]
        if self.corners.shape[0] == 0 and self.adjusted_corners.shape[0] == 0:
            seg.corners, seg.adjusted_corners = self.auto_detect()
        
        if seg.adjusted_corners.shape[0] != 0:
            if self.verbosity > 1:
                print("loading corners from save")
            seg.corners = self.convert_backward(*seg.adjusted_corners)
            # self.adjusted_corners = self.convert_points_forward(*self.corners)

        if self.verbosity > 1:
            print("adjusted corners:", seg.adjusted_corners)
            print("corners to warp on:", seg.corners)

        persp_img = self.cv_image.copy()
        for seg in self.segmentations:
            if seg.corners.shape[0] % 4 != 0:
                if self.verbosity > 0:
                    print("Bad Image")
                self.skip = True
                persp_img = self.cv_image
            else:
                self.skip = False
                self.cv_warp_image, self.trans_matrix = four_point_transform(self.cv_image, self.corners)
                vert_lines, hor_lines = self.calculate_lines(self.cv_warp_image, seg)
                vert_warp_lines, hor_warp_lines = self.untransform_lines(vert_lines, hor_lines)
                # Adding lines to persp_img
                self.apply_grid(persp_img, vert_warp_lines[0], reversed(vert_warp_lines[1]))
                self.apply_grid(persp_img, hor_warp_lines[0], reversed(hor_warp_lines[1]))

                seg.vert_lines, seg.hor_lines = vert_warp_lines, hor_warp_lines

        # Converting persp_img
        persp_img = cv2.cvtColor(persp_img, cv2.COLOR_BGR2RGB)
        persp_img = Image.fromarray(persp_img)
        self.pil_image = persp_img.resize(self.resize)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        return True

    def get_bb(self):
        v_lines1, v_lines2 = self.vert_lines[0], reversed(self.vert_lines[1])
        h_lines1, h_lines2 = self.hor_lines[0], reversed(self.hor_lines[1])

        v_lines = [(p1, p2) for p1, p2 in zip(v_lines1, v_lines2)]
        h_lines = [(p1, p2) for p1, p2 in zip(h_lines1, h_lines2)]
        
        all_segmentations = []
        for i in range(len(v_lines)-1):
            for j in range(len(h_lines)-1):
                # Get all points CCW
                segmentation = []
                segmentation.append(self._get_intersection(v_lines, h_lines, i, j))
                segmentation.append(self._get_intersection(v_lines, h_lines, i+1, j))
                segmentation.append(self._get_intersection(v_lines, h_lines, i+1, j+1))
                segmentation.append(self._get_intersection(v_lines, h_lines, i, j+1))
                all_segmentations.append(segmentation)
        return all_segmentations

    def _get_intersection(self, line1, line2, i, j):
        return find_intersection(
            line1[i][0][0], 
            line1[i][0][1], 
            line1[i][1][0],
            line1[i][1][1],
            line2[j][0][0],
            line2[j][0][1],
            line2[j][1][0],
            line2[j][1][1],
            )

    def untransform_lines(self, vert_lines, hor_lines):
        inv_trans = np.linalg.pinv(self.trans_matrix)
        vert_warp_lines = []
        hor_warp_lines = []
        for line in vert_lines:
            vert_warp_lines.append([self.transform_point(p, inv_trans) for p in line])
        for line in hor_lines:
            hor_warp_lines.append([self.transform_point(p, inv_trans) for p in line])
        return vert_warp_lines, hor_warp_lines

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
        self.image = self.canvas.create_image(0, 0, anchor = tk.NW, image=None)

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

        self.canvas.addtag_withtag('selected', tk.CURRENT)

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