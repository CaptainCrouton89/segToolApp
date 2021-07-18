from pathlib import Path
from datetime import date
import json
from shapely.geometry import Polygon
from PIL import Image, ImageTk
from warpTools import four_point_transform
import cornerDetectionTools
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

keybinds = "\n\
    \n\tFILE MANIPULATION ******************\t\
    \n\
    \n\tOpen directory          <Control-o> \
    \n\tSave annotations        <Control-s> \
    \n\
    \n\
    \n\tNAVIGATING BETWEEN FRAMES **********\t\
    \n\
    \n\tNext frame              <f> \
    \n\tPrevious frame          <d> \
    \n\tSkip frame              <Shift-k> \
    \n\
    \n\
    \n\tSEGMENTATION ***********************\t\
    \n\
    \n\tReset                   <Control-r> \
    \n\tSet dimensions          <Return> \
    \n\tSwitch dimensions       <x> \
    \n\tIncrease rows           <Right> \
    \n\tDecrease rows           <Left> \
    \n\tIncrease columns        <Up> \
    \n\tDecrease columns        <Down> \
    \n\tNew segmentation        <Shift-n> \
    \n\tSwitch segmentations    <Tab> \
    \n\n"

instructions = "\
    \n\
    \n\tOPEN THE DIRECTORY ************************************************     \
    \n\tClick browse (<Control-o>) to open a directory on your local     \
    \n\tmachine. Then navigate to the folder containing the images you wish \
    \n\tto segment, and open that folder. \
    \n\
    \n\tSEGMENT THE IMAGES ************************************************     \
    \n\tThe application will try to automatically find the corners of the \
    \n\timage for you, and will place four white circles at each corner. \
    \n\tHowever, it does not always succeed, in which case you will \
    \n\tmanually need to select the corners. You can place a corner by \
    \n\tholding shift while clicking on the image. Once four corners have \
    \n\tbeen placed, it will automatically draw the segmentation, and you \
    \n\tcan proceed to the next one (<f>) or go back (<d>).\
    \n\
    \n\tYou may find that the segmentation grid does not line up perfectly \
    \n\twith the cells of the solar panel. In this case, you can click and \
    \n\tdrag the corners as you please. If the image still does not line up \
    \n\tyou can add an additional segmentation grid with <Control-n>. You \
    \n\tcan click and drag points from either segmentation grid. If you \
    \n\twantto add more points, make sure you are on the correct \
    \n\tsegmentation grid, as indicated by the number in the top right, to \
    \n\tthe right of the 'Recalculate' button. You can switch which grid \
    \n\tyou are adding points to by hitting <Tab>.\
    \n\
    \n\tIf you mess up, and would like to start over at any time, you can \
    \n\thit 'Recalculate' (<Control-r>) and it will reset. \
    \n\
    \n\tYou may also find that you need to adjust the dimensions of the \
    \n\tgrid. If this is the case, manually typing in the dimensions in the \
    \n\ttop left, or using the arrow keys will let change the number of  \
    \n\trows and columns in the grid. You can also switch the dimensions of \
    \n\tthe grid by clicking the 'Switch dimensions' button (<x>). \
    \n\
    \n\tIf an image is unsaveable, you can skip the image by pressing \
    \n\t<Shift-k>. This will force the application to skip this image when \
    \n\texporting the annotation file. \
    \n\
    \n\tSAVE, EXPORT, UPLOAD*********************************************** \
    \n\tOnce you are finished, save the annotation file (<Control-s>). The \
    \n\tfile will be saved to the same location as the images with the name \
    \n\t'annotations.json'. \
    \n\
    \n\tYou may need to also upload these to the azure file share. If you \
    \n\thave access to it, the entire folder should be uploaded in the share \
    \n\
    \n\t/File Shares/pv-segment-training/clean-segmentation-data-for-training \
    \n\
    \n\tand the folder containing the images and annotation should be \
    \n\trenamed to the date and time in the format 'yyyy-mm-dd hh.mm'. For \
    \n\texample, '2021-07-15 14.03'. \
    \n\t\
\n"

def recursive_map(f, it):
    return (recursive_map(f, x) if isinstance(x, tuple) else f(x) for x in it)


class App():

    def __init__(self, name, verbosity=0, in_folder=None):
        self.default_in_folder = in_folder

        self.verbosity = verbosity        

        self.root = self.draw_window(name)
        self.root.bind('<Return>', self.set_dims)
        self.root.bind('<x>', self.switch_dims)
        self.root.bind('<Control-r>', self.recalculate_corners)
        self.root.bind('<f>', self._next_frame)
        self.root.bind('<d>', self._prev_frame)
        self.root.bind('<Right>', self.increase_width)
        self.root.bind('<Left>', self.decrease_width)
        self.root.bind('<Up>', self.increase_height)
        self.root.bind('<Down>', self.decrease_height)
        self.root.bind('<Control-o>', self.load_images)
        self.root.bind('<Control-s>', self.save_to)
        self.root.bind('<K>', self.skip)
        self.root.bind('<N>', self.new_segmentation)
        self.root.bind('<Tab>', self.persp_image.next_index)

    def run(self):
        self.root.mainloop()
        self.refresh()

    def open_keybinds(self, event=None):
        keybind_win = tk.Toplevel(self.root)
        keybind_win.title("Keybinds")
        text = tk.Label(keybind_win, anchor='w', justify=tk.LEFT, text=keybinds)
        text.configure(font=("Menlo", 14))
        text.pack(side=tk.LEFT, fill="both")

    def open_instructions(self, event=None):
        inst_win = tk.Toplevel(self.root)
        inst_win.title("Instructions")
        text = tk.Label(inst_win, anchor='w', justify=tk.LEFT, text=instructions)
        text.configure(font=("Menlo", 14))
        text.pack(side=tk.LEFT, fill="both")

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
        header.columnconfigure([0, 5], minsize=50)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)
        header.columnconfigure(3, weight=1)
        header.columnconfigure(4, weight=1)
        header.columnconfigure(5, weight=1)

        self.name = tk.Label(master=header, text="NAME", fg="black")
        self.name.grid(row=0, column=0, columnspan=6, sticky="nsew")

        bt_keybinds = tk.Button(header, text="Keybinds", command=self.open_keybinds, takefocus=0, fg="black")
        bt_keybinds.grid(row=3, column=0, sticky="nsew")

        bt_instructions = tk.Button(header, text="Instructions", command=self.open_instructions, takefocus=0, fg="black")
        bt_instructions.grid(row=3, column=1, sticky="nsew")

        bt_browse = tk.Button(header,text="Browse",command=self.load_images, takefocus=0, fg="black")
        bt_browse.grid(row=3, column=4, sticky="nsew")

        bt_save = tk.Button(header, text="Save",command=self.save_to, fg="black")
        bt_save.grid(row=3, column=5, sticky="nsew")
        return header

    def _draw_nav(self, content):
        navbar = tk.Frame(master=content, padx=3, pady=3, width=600, height=10, borderwidth=5, relief="ridge")

        navbar.columnconfigure([0, 5], minsize=50)

        navbar.columnconfigure(0, weight=1)
        navbar.columnconfigure(1, weight=1)
        navbar.columnconfigure(2, weight=1)
        navbar.columnconfigure(3, weight=1)
        navbar.columnconfigure(4, weight=1)
        navbar.columnconfigure(5, weight=1)


        bt_next = tk.Button(navbar, text="Next", command=self._next_frame, takefocus=0, fg="black")
        bt_next.grid(row=1, column=5, sticky=("nsew"))

        bt_prev = tk.Button(navbar, text="Previous", command=self._prev_frame, takefocus=0, fg="black")
        bt_prev.grid(row=1, column=0, sticky=("nsew"))

        
        return navbar

    def _draw_editor(self, content):
        editor_frame = tk.Frame(master=content, padx=3, pady=3, width=600, height=5, borderwidth=5, relief="ridge")
        self.editor_frame = editor_frame

        controls_frame = tk.Frame(master=editor_frame)
        controls_frame.pack(side=tk.TOP, fill="x")

        self.pv_width = tk.Entry(master=controls_frame, width=3, fg="black", bg="white", takefocus=0)
        self.pv_height = tk.Entry(master=controls_frame, width=3, fg="black", bg="white", takefocus=0)
        self.bt_setdim = tk.Button(master=controls_frame, text="Confirm dimensions", command=self.set_dims, fg="black")
        self.bt_switchdim = tk.Button(master=controls_frame, text="Switch dimensions", command=self.switch_dims, fg="black")
        bt_recal_corners = tk.Button(controls_frame, text="Recalculate",command=self.recalculate_corners, fg="black")
        self.lb_seg_index = tk.Label(controls_frame, text="Segmentation: 1", fg="black", takefocus=0)


        self.pv_width.delete(0, 'end')
        self.pv_height.delete(0, 'end')
        self.pv_width.insert(tk.END, 10)
        self.pv_height.insert(tk.END, 6)

        self.pv_width.pack(side=tk.LEFT)
        self.pv_height.pack(side=tk.LEFT)
        self.bt_setdim.pack(side=tk.LEFT)
        self.bt_switchdim.pack(side=tk.LEFT)
        bt_recal_corners.pack(side=tk.LEFT)
        
        self.lb_seg_index.pack(side=tk.LEFT)

        self.draw_image_frames(editor_frame)
        return editor_frame

    def draw_image_frames(self, editor_frame):
        self.persp_frame = Frame(editor_frame, width=200, height=200, borderwidth=0)
        self.persp_frame.pack(side=tk.TOP, fill="both", expand=True)

        self.persp_image = PerspectiveView(self, self.persp_frame, self.verbosity)
        self.persp_image.canvas.pack(side=tk.TOP, fill="both", expand=True)

    def load_images(self, event=None):
        w, h = self.persp_image.canvas.winfo_width(), self.persp_frame.winfo_height()
        print(w, h)
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
                self.all_images.append(ImageLoad(filepath, resize=(int(.99 * w), int(.975 * h)), verbosity=self.verbosity))
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
                for segmentation_grid in all_segmentations:
                    for segmentation in segmentation_grid:
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
        self.persp_image.seg_index = 0
        self._next_frame()

    def set_dims(self, event=None):
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].x_cells = int(self.pv_width.get())
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].y_cells = int(self.pv_height.get())
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
        img_load = self.persp_image.image_load
        self.persp_image.reset()
        img_load.segmentations[0].corners, img_load.segmentations[0].adjusted_corners = self.persp_image.image_load.auto_detect()
        self.refresh()

    def new_segmentation(self, event=None):
        self.persp_image.new_segmentation()

    def refresh_dims(self):
        self.pv_width.delete(0, 'end')
        self.pv_height.delete(0, 'end')
        x = self.persp_image.image_load.segmentations[self.persp_image.seg_index].x_cells
        y = self.persp_image.image_load.segmentations[self.persp_image.seg_index].y_cells
        self.pv_width.insert(tk.END, x)
        self.pv_height.insert(tk.END, y)

    def increase_width(self, event=None):
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].x_cells += 1
        self.refresh_dims()
        self.refresh()

    def decrease_width(self, event=None):
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].x_cells -= 1
        self.refresh_dims()
        self.refresh()

    def increase_height(self, event=None):
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].y_cells += 1
        self.refresh_dims()
        self.refresh()

    def decrease_height(self, event=None):
        self.persp_image.image_load.segmentations[self.persp_image.seg_index].y_cells -= 1
        self.refresh_dims()
        self.refresh()


class Segmentation():

    def __init__(self):
        self.x_cells = 10
        self.y_cells = 6
        self.corners = np.array([])
        self.adjusted_corners = np.array([])
        self.vert_lines = []
        self.hor_lines = []
        self.cv_warp_image = None
        self.trans_matrix = None

    def reset(self):
        self.corners = np.array([])
        self.adjusted_corners = np.array([])
        self.vert_lines = []
        self.hor_lines = []
        self.cv_warp_image = None
        self.trans_matrix = None

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

        self.height, self.width, _ = self.cv_image.shape

        # Persp shift vars
        self.resize_factor = (resize[0]/self.width, resize[1]/self.height)
        if (self.verbosity > 1):
            print("resize:", resize)
            print("resize factor:", self.resize_factor)
    
        self.segmentations = [Segmentation()]

    def new_segmentation(self):
        self.segmentations.append(Segmentation())

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
        if self.verbosity > 1:
            print("Refreshing image_load")
        global default_image
        # If points never set yet, will auto-calculate best guess
        seg = self.segmentations[0]
        if seg.corners.shape[0] == 0 and seg.adjusted_corners.shape[0] == 0:
            seg.corners, seg.adjusted_corners = self.auto_detect()
    
        persp_img = self.cv_image.copy()
        self.skip = False
        for seg in self.segmentations:
            if self.verbosity > 1:
                print("adjusted corners:", seg.adjusted_corners)
                print("corners to warp on:", seg.corners)
            if seg.adjusted_corners.shape[0] != 0:
                if self.verbosity > 1:
                    print("loading corners from save")
                seg.corners = self.convert_backward(*seg.adjusted_corners)
                # self.adjusted_corners = self.convert_points_forward(*self.corners)
            corner_count = seg.corners.shape[0]
            if corner_count != 4:
                if self.verbosity > 0:
                    if corner_count == 0:
                        print("Hint: Hold down shift and click on the corners of the panel to add a segmentation \
                                or press <Control-k> to skip this image.")
                    if corner_count % 4 == 0:
                        print("Hint: Did you forget to create a new segmentation? Press recalculate and then \
                                <Control-n> to create a new segmentation. You can press <Tab> to switch between \
                                them.")
                self.skip = True
                persp_img = self.cv_image
            else:
                seg.cv_warp_image, seg.trans_matrix = four_point_transform(self.cv_image, seg.corners)
                vert_lines, hor_lines = self.calculate_lines(seg.cv_warp_image, seg)
                vert_warp_lines, hor_warp_lines = self.untransform_lines(vert_lines, hor_lines, seg)
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
        all_segmentations = []
        for segmentation in self.segmentations:
            v_lines1, v_lines2 = segmentation.vert_lines[0], reversed(segmentation.vert_lines[1])
            h_lines1, h_lines2 = segmentation.hor_lines[0], reversed(segmentation.hor_lines[1])

            v_lines = [(p1, p2) for p1, p2 in zip(v_lines1, v_lines2)]
            h_lines = [(p1, p2) for p1, p2 in zip(h_lines1, h_lines2)]
            
            sementation_grid = []
            for i in range(len(v_lines)-1):
                for j in range(len(h_lines)-1):
                    # Get all points CCW
                    segmentation = []
                    segmentation.append(self._get_intersection(v_lines, h_lines, i, j))
                    segmentation.append(self._get_intersection(v_lines, h_lines, i+1, j))
                    segmentation.append(self._get_intersection(v_lines, h_lines, i+1, j+1))
                    segmentation.append(self._get_intersection(v_lines, h_lines, i, j+1))
                    sementation_grid.append(segmentation)
            all_segmentations.append(sementation_grid)
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

    def untransform_lines(self, vert_lines, hor_lines, seg):
        inv_trans = np.linalg.pinv(seg.trans_matrix)
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


class PerspectiveView():
    
    radius = 3

    def __init__(self, app, master, verbosity=0):
        self.app = app
        self.verbosity = verbosity

        self.selected = None

        self.canvas = Canvas(master, width=500, height=500)

        self.image = self.canvas.create_image(10, 10, anchor=tk.NW, image=None)

        self.canvas.bind('<1>', self.select_circle)
        self.canvas.bind('<Shift-1>', self.make_circle)
        # self.canvas.bind('<Control-1>', self.delete_circle)
        self.seg_index = 0

        self.can_draw = True

        self.indicators = [[]]

    def reset(self):
        for segmentation in self.image_load.segmentations:
            segmentation.reset()
        self.clear_all()
        self.indicators = [[]]
        self.image_load.segmentations = [Segmentation()]
        self.next_index()

    def next_index(self, event=None):
        max_index = len(self.indicators)
        self.seg_index += 1
        if self.seg_index >= max_index:
            self.seg_index = 0
        self.app.lb_seg_index.configure(text="Segmentation: " + str(self.seg_index + 1))
        if self.verbosity > 0:
            print("Current index:", self.seg_index)

    def allow_draw(self, event=None):
        self.can_draw = True

    def make_circle(self, event):
        if self.can_draw:
            self.canvas.after(200, self.allow_draw)
            x, y, r = event.x, event.y, self.radius
            self.indicators[self.seg_index].append(self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', fill='white'))
            if self.verbosity > 1:
                print("Created point in indicator list #", self.seg_index)
                print("All indicators, after cicking to draw point:", self.indicators)
            self.update_corners()
            self.can_draw = False

    def delete_circle(self, event):
        x, y, r = event.x, event.y, self.radius
        iid = self.canvas.find_enclosed(x - 26, y - 26, x + 26, y + 26)
        for widget in iid:
            self.canvas.delete(widget)
        self.refresh()
        self.update_corners()

    def clear_all(self):
        if self.verbosity > 0:
            print("Clearing points")
        for seg_indicators in self.indicators:
            for point in seg_indicators:
                self.canvas.delete(point)

    def set_image(self, image_load):
        self.image_load = image_load

    def select_circle(self, event):
        self.canvas.bind('<Motion>', self.move_circle)
        self.canvas.bind('<ButtonRelease-1>', self.deselect)

        self.canvas.addtag_withtag('selected', tk.CURRENT)

    def move_circle(self, event):
        min_x, min_y, max_x, max_y = 0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()
        x, y, r = event.x, event.y, self.radius
        try:
            
            if x > max_x:
                x = max_x
            if y > max_y:
                y = max_y
            if x < min_x:
                x = min_x
            if y < min_y:
                y = min_y
            self.canvas.coords('selected', x-r, y-r, x+r, y+r)
        except:
            if self.verbosity > 1:
                print("\tYou can't select/move the background canvas")

    def deselect(self, event):
        self.update_corners()
        self.canvas.dtag('selected')    # removes the 'selected' tag
        self.canvas.unbind('<Motion>')
        self.canvas.bind('<Shift-1>', self.make_circle)
      
    def update_corners(self):
        if self.verbosity > 1:
            print("Transferring clicked points to image_load")
            print("\tCurrent segmentations list:", self.image_load.segmentations)
            print("\tCurrent indicator list:", self.indicators)
        if self.indicators[0]:
            for seg, indicator_list in zip(self.image_load.segmentations, self.indicators):
                
                corners = []
                for widget in indicator_list:
                    x1, y1, _, _ = self.canvas.coords(widget)
                    corners.append([x1+self.radius, y1+self.radius])
                seg.adjusted_corners = np.asarray(corners)
            self.app.refresh()
        
    def refresh(self):
        r = self.radius
        self.canvas.itemconfig(self.image, image = self.image_load.tk_image)
        for indicator_list in self.indicators:
            indicator_list.clear()
        for seg, indicator_list in zip(self.image_load.segmentations, self.indicators):
            for p in seg.adjusted_corners:
                x, y = int(p[0]), int(p[1])
                indicator_list.append(self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='black', fill='white'))

    def new_segmentation(self):
        self.image_load.new_segmentation()
        self.indicators.append([])
        self.next_index()
        if self.verbosity > 1:
            print("Indicators after adding segmentation:", self.indicators)


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