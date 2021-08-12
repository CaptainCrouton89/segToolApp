# App for Easy, Mass Segmentation of Solar Panel Cells
In order to train a model to automatically detecect and mask individual cells of a solar panel, the model needs a significant amount of training data—examples of correctly detected and masked cells. Manually doing this is difficult—most 3rd party softwares let you mask out shapes, but doing this for each individual cell in a 6x10 solar panel means meticulously drawing 60 quadrilaterals on an image. It's fatiguing, takes forever, and frequently doesn't come out great.

This where this app comes in. You can load up a batch of solar panel images, and then click through them, segmenting them. The app has a number of inbuilt tools specifically designed for segmenting images of solar panels, speeding up this process drastically. At the end, you can save these annotations (a COCO formate .json file describing the coordinates of your masking) generated from your segmenation and upload it to Azure Storage, where it can then be used by the machine learning team to train the segmentation model.

## Installation
1. Download SegmenterWindowsBuild.exe.zip or SegmenterMacBuild.zip. You can do this by clicking on the file, and then hitting the download button in the upper right.
2. Unzip the file.
3. Move the app to whatever directory you wish to run it from (applications folder, usually).

## Using the Application
1. Double click the icon to open the app. This will take some time—usually around 15 seconds. Upon opening, resize the window to your prefered workspace size. Once the images have loaded, you won't be able to resize again.
2. Hit browse. Navigate to a folder with the images of solar panels you want to segment, and open it. This will take a while to load, depending on the size and number of images. It is advisable not to load a folder with more than 50 images. WARNING: On windows, you will not be able to see the image files when navigating with the file explorer. Don't worry—they will still load fine if you have chosen the correct folder.
3. Check out the instructions by hitting the instructions button, and take a look at the keybinds. These are a good reference if you don't know how something works while you are using the app.
4. Begin segmentation. The specifics of this process are outlined below.

## Segmentation
The general outline of this process consists of going from image to image, marking the corners of the solar panel, and adjusting the number of grid lines that are overlayed over the panel. The app will interpret each square within the grid as a panel, so it's critical that you line the grid up with the solar panel well.

### Aligning the Grid
When the first image loads in, there may or may not already be a grid overlaid on your image. If there is, it is because the app's rudimentary corner detection found 4 corners and placed the corners of the grid on each of those corners. If there is no grid, or the corners or grid are wrong, that's okay.

If there is no grid, you can add one by holding the ```Shift``` key, and clicking on the image. Click once on each of the four corners of the solar panel to place a grid over that panel. The grid will not appear until all four corners have been placed. If you add too many corners (more than 4), then the grid will disappear again, and you will need to start over. To do this, hit the ```Recalculate``` button.

If the grid does exist, but doesn't line up with the cells, you can adjust the corners of the grid by clicking and dragging the white circles at each corner. Once you have aligned the corners, you can change the number of rows and columns of the grid. 

To change the grid dimensions, you can use the arrow keys, or you can manually enter the dimensions in the text boxes at the top. If you are using the text boxes, you can hit ```Return``` to submit those dimensions. Likewise, if you have set the dimensions already, and want to use those same dimensions for the next image as well, hitting ```Return``` will automatically use the dimensions you last typed into the text boxes.

If the grid still doesn't line up with the cells (for example, if you have two panels close together making up one module), then you may need to make a *second segmentation*. To do this, first adjust the corners and grid dimensions over one of the panels. Once you are satisfied, you can make a second segmentation by pressing ```Shift + n```. The segmentation counter at the top will now say "2" if this is the second segmentation for this image. You may now use ```Shift + Click``` to add additional corners. 

**A FEW NOTES**
* Remember—at any time, you can hit ```Recalculate``` to start over on that image.
* If you realize that you don't want to segment this image, you don't want it in your data, or for any other reason, you can skip that image by hitting the ```Skip``` button or pressing ```Shift + k```. 

### Everything Else
Once you have aligned the grid(s) to your liking, you can go to the next image by hitting ```Next``` or ```f``` on your keyboard. Likewise, if you realize you have messed up, you can go back by hitting ```Back``` or ```d``` on your keyboard.

All images are, by default, marked as "to skip". It is only by hitting the next key that the image is marked as safe to keep. For this reason, you can save at any point during segmentation and keep all of your work so far. Although you can save a session half-way through a batch, however, you cannot resume from where you left off, and it will create a new annotation file. Note that the app will not save the image you are currently working on until you go to the next image. If you want to save every image, you will need to hit next after the very last image, looping you back around, and then hit save/save export

To save your segmentations, you have two options: ```Save```, and ```Save + Export```. ```Save``` will save all of the images to another folder, inside the original image folder. Within that folder will be all of the images, along with a file called ```annotations.json```. This is where all of the COCO formatted segmentation data is stored.

```Save + Export``` has the same functionality as ```Save```, except it also uploads it to the cloud. *This is the option you should choose* unless you are testing the application, or are not working for Clean Energy Associates. 


## SPECS
* File size
* Generates COCO format .json file
* Exports to ```pv-storage/pvSegmentationTraining/segmentation-output/<date in yyyy-mm-dd-hh-mm-ss format>/```
