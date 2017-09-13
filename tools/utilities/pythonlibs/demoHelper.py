####################################################################################################
##
##  Project:  Embedded Learning Library (ELL)
##  File:     demoHelper.py
##  Authors:  Chris Lovett
##            Byron Changuion
##
##  Requires: Python 3.x
##
####################################################################################################

import os
import sys
import argparse
import cv2
import numpy as np
import time
import math

script_path = os.path.dirname(os.path.abspath(__file__))

def get_common_commandline_args(argv, helpString=""):
    """
    Parses common commandline arguments for ELL tutorials and demos and returns an object with the relevant values set from those arguments.
    """
    arg_parser = argparse.ArgumentParser(helpString)

    # required arguments
    arg_parser.add_argument("labels", help="path to the labels file for evaluating the model, or comma separated list if using more than one model")

    # options
    arg_parser.add_argument("--iterations", type=int, help="limits how many times the model will be evaluated, the default is to loop forever")
    arg_parser.add_argument("--save", help="save images captured by the camera", action='store_true')
    arg_parser.add_argument("--threshold", type=float, help="threshold for the minimum prediction score. A lower threshold will show more prediction labels, but they have a higher chance of being completely wrong.", default=0.15)

    # mutually exclusive options
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("--camera", type=int, help="the camera id of the webcam", default=0)
    group.add_argument("--image", help="path to an image file. If set, evaluates the model using the image, instead of a webcam")
    group.add_argument("--folder", help="path to an image folder. If set, evaluates the model using the images found there")

    group2 = arg_parser.add_mutually_exclusive_group()
    group2.add_argument("--model", help="path to a model file")
    group2.add_argument("--compiledModel", help="path to the compiled model's Python module")
    group2.add_argument("--models", help="list of comma separated paths to model files")
    group2.add_argument("--compiledModels", help="list of comma separated paths to the compiled models' Python modules")

    args = arg_parser.parse_args(argv)
    return args

# Helper class that interfaces with ELL models to get predictions and provides handy conversion from opencv to ELL buffers and 
# rendering utilties
class DemoHelper:
    def __init__(self, threshold=0.25):
        """ Helper class to store information about the model we want to use.
        argv       - arguments passed in from the command line 
        threshold   - specifies a prediction threshold. We will ignore prediction values less than this
        """

        self.threshold = threshold
        self.start = time.time()
        self.frame_count = 0
        self.fps = 0
        self.camera = 0
        self.image_filename = None
        self.image_folder = None
        self.images = None
        self.image_pos = 0
        self.capture_device = None
        self.frame = None
        self.save_images = None
        self.image_index = 0
        self.model_file = None
        self.model = None
        self.model_name = "model"
        self.compiled_model = None
        self.compiled_module = None
        self.compiled_func = None
        self.labels_file = None
        self.model_file = None
        self.iterations = None  # limit number of iterations through the loop.
        self.total_time = 0
        self.time_count = 0
        self.warm_up = True
        self.input_shape = None
        self.output_shape = None

    def parse_arguments(self, argv, helpString):
        args = get_common_commandline_args(argv, helpString)
        self.initialize(args)

    def value_from_arg(self, argValue, defaultValue):
        if (argValue is not None):
            return argValue
        return defaultValue

    def initialize(self, args):
        # called after parse_args to extract args from the arg_parser.
        # process required arguments
        self.labels_file = args.labels

        # process options
        self.save_images = self.value_from_arg(args.save, None)
        self.threshold = self.value_from_arg(args.threshold, None)
        self.iterations = self.value_from_arg(args.iterations, None)
        self.camera = self.value_from_arg(args.iterations, 0)
        self.image_filename = self.value_from_arg(args.image, None)
        self.image_folder = self.value_from_arg(args.folder, None)

        # process image source options
        if (args.camera):
            self.image_filename = None
            self.image_folder = None
        elif (args.image):
            self.camera = None
            self.image_folder = None
        elif (args.folder):
            self.camera = None

        # load the labels
        self.labels = self.load_labels(self.labels_file)
        
        # process model options and load the model
        self.model_file = args.model
        self.compiled_model = args.compiledModel
        if (self.model_file == None):
            # this is the compiled model route, so load the wrapped module
            self.model_name = os.path.split(self.compiled_model)[1]
            self.import_compiled_model(self.compiled_model, self.model_name)
        else:
            # this is the "interpreted" model route, so we need the ELL runtime.
            self.model_name = os.path.splitext(self.model_file)[0]
            self.import_ell_map()
            
        self.input_size = (self.input_shape.rows, self.input_shape.columns)
        
        print("Found input_shape [%d,%d,%d]" % (self.input_shape.rows, self.input_shape.columns, self.input_shape.channels))
        return True

    def import_ell_map(self):
        sys.path.append(script_path)
        sys.path.append(os.getcwd())
        print("### Loading ELL modules...")
        __import__("find_ell")
        ELL = __import__("ELL")            
        ell_utilities = __import__("ell_utilities")
        print("loading model: " + self.model_file)
        self.model = ELL.ELL_Map(self.model_file)
        self.input_shape = self.model.GetInputShape()
        self.output_shape = self.model.GetOutputShape()

    def import_compiled_model(self, compiledModulePath, name):
        moduleDirectory = os.path.dirname(compiledModulePath)
        print('Looking for: ' + name + ' in ' + moduleDirectory)
        if (not os.path.isdir('build')) and (not os.path.isdir(moduleDirectory + '/build')):
            raise Exception("you don't have a 'build' directory, have you compiled this project yet?")

        func_name = 'predict'
        if func_name == "":
            raise Exception("Could not construct func name. Is the --compiledModel argument correct?")
        
        # Import the compiled model wrapper. Add the possible build directories.
        sys.path.append(script_path)
        sys.path.append(moduleDirectory)
        sys.path.append(os.path.join(moduleDirectory, 'build'))
        sys.path.append(os.path.join(moduleDirectory, 'build/Release'))
        sys.path.append(os.path.join(script_path, 'build'))
        sys.path.append(os.path.join(script_path, 'build/Release'))
        sys.path.append(os.path.join(os.getcwd(), 'build'))
        sys.path.append(os.path.join(os.getcwd(), 'build/Release'))
        try:
            self.compiled_module = __import__(name)
            
            inputShapeGetter = getattr(self.compiled_module, "get_default_input_shape")
            outputShapeGetter = getattr(self.compiled_module, "get_default_output_shape")
            self.input_shape = inputShapeGetter()
            self.output_shape = outputShapeGetter()

            size = int(self.output_shape.rows * self.output_shape.columns * self.output_shape.channels)
            self.results = self.compiled_module.FloatVector(size)
            try:
                self.compiled_func = getattr(self.compiled_module, func_name)
            except AttributeError:
                raise Exception(func_name + " function not found in compiled module")
        except:    
            errorType, value, traceback = sys.exc_info()
            print("### Exception: " + str(errorType) + ": " + value)
            print("====================================================================")
            print("Compiled ELL python module is not loading")
            print("It is possible that you need to add LibOpenBLAS to your system path (See Install-*.md) from root of this repo")
            raise Exception("Compiled model failed to load")

    def show_image(self, frameToShow, save):
        cv2.imshow('frame', frameToShow)
        if save and self.save_images:
            name = 'frame' + str(self.image_index) + ".png"
            cv2.imwrite(name, frameToShow)
            self.image_index = self.image_index + 1

    def load_labels(self, fileName):
        labels = []
        with open(fileName) as f:
            labels = f.read().splitlines()
        return labels

    def predict(self, data):
        if self.iterations != None:
            self.iterations = self.iterations - 1
        start = time.time()
        if self.model == None:
            self.compiled_func(data, self.results)
        else:
            self.results = self.model.ComputeFloat(data)
        end = time.time()
        diff = end - start

        # if warm up is true then discard the first time
        if self.time_count == 1 and self.warm_up:
            self.warm_up = False
            self.total_time = 0
            self.time_count = 0

        self.total_time = self.total_time + diff
        self.time_count = self.time_count + 1
        return self.results

    def get_times(self):
        """Returns the average prediction time, if available."""
        average_time = None
        if self.time_count > 0:
            average_time = self.total_time/self.time_count
        return average_time

    def report_times(self):
        """Prints the average prediction time, if available."""
        average_time = self.get_times()
        if average_time is not None:
            print("Average prediction time: " + str(average_time))

    def get_top_n(self, predictions, N):
        """Return at most the top N predictions as a list of tuples that meet the threshold."""
        topN = np.zeros([N, 2])

        for p in range(len(predictions)):
            for t in range(len(topN)):
                if predictions[p] > topN[t][0]:
                    topN[t] = [predictions[p], p]
                    break
        result = []
        for element in topN:
            if element[0] > self.threshold:
                i = int(element[1])
                result.append((i, element[0]))
        return result

    def get_label(self, i):
        if (i < len(self.labels)):
            return self.labels[i]
        return ""

    def get_predictor_map(self, predictor, intervalMs):
        """Creates an ELL map from an ELL predictor"""
        import ell_utilities

        name = self.model_name
        if intervalMs > 0:
            ell_map = ell_utilities.ell_steppable_map_from_float_predictor(
                predictor, intervalMs, name + "InputCallback", name + "OutputCallback")
        else:
            ell_map = ell_utilities.ell_map_from_float_predictor(predictor)
        return ell_map

    def save_ell_predictor_to_file(self, predictor, filePath, intervalMs=0):
        """Saves an ELL predictor to file so that it can be compiled to run on a device, with an optional stepInterval in milliseconds"""
        ell_map = self.get_predictor_map(predictor, intervalMs)
        ell_map.Save(filePath)

    def init_image_source(self):
        # Start video capture device or load static image
        if self.camera is not None:
            self.capture_device = cv2.VideoCapture(self.camera)
        elif self.image_filename:
            self.frame = cv2.imread(self.image_filename)
            if (type(self.frame) == type(None)):
                raise Exception('image from %s failed to load' %
                                (self.image_filename))
        elif self.image_folder:
            self.frame = self.load_next_image()
    
    def load_next_image(self):
        if self.images == None:
            self.images = os.listdir(self.image_folder)
        frame = None
        while frame is None and self.image_pos < len(self.images):
            filename = os.path.join(self.image_folder, self.images[self.image_pos])
            frame = cv2.imread(filename)
            self.image_pos += 1
        if not frame is None:
            return frame
        return self.frame

    def get_next_frame(self):
        if self.capture_device is not None:
            # if predictor is too slow frames get buffered, this is designed to flush that buffer
            for i in range(self.get_wait()):
                ret, self.frame = self.capture_device.read()
            if (not ret):
                raise Exception('your capture device is not returning images')
            return self.frame
        else:
            return np.copy(self.frame)

    def resize_image(self, image, newSize):
        # Shape: [rows, cols, channels]
        """Crops, resizes image to outputshape. Returns image as numpy array in in RGB order."""
        if image.shape[0] > image.shape[1]:  # Tall (more rows than cols)
            rowStart = int((image.shape[0] - image.shape[1]) / 2)
            rowEnd = rowStart + image.shape[1]
            colStart = 0
            colEnd = image.shape[1]
        else:  # Wide (more cols than rows)
            rowStart = 0
            rowEnd = image.shape[0]
            colStart = int((image.shape[1] - image.shape[0]) / 2)
            colEnd = colStart + image.shape[0]

        cropped = image[rowStart:rowEnd, colStart:colEnd]
        resized = cv2.resize(cropped, newSize)
        return resized

    def prepare_image_for_predictor(self, image):
        """Crops, resizes image to outputshape. Returns image as numpy array in in RGB order."""        
        resized = self.resize_image(image, self.input_size)
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        resized = resized.astype(np.float).ravel()
        return resized

    def draw_label(self, image, label):
        """Helper to draw text label onto an image"""
        self.draw_header(image, label)
        return

    def draw_header(self, image, text):
        """Helper to draw header text block onto an image"""
        self.draw_text_block(image, text, (0, 0), (50, 200, 50))
        return

    def draw_footer(self, image, text):
        """Helper to draw footer text block onto an image"""
        self.draw_text_block(image, text, (0, image.shape[0] - 40), (200, 100, 100))
        return

    def draw_text_block(self, image, text, blockTopLeft=(0,0), blockColor=(50, 200, 50), blockHeight=40, fontScale=0.7):
        """Helper to draw a filled rectangle with text onto an image"""
        cv2.rectangle(
            image, blockTopLeft, (image.shape[1], blockTopLeft[1] + blockHeight), blockColor, cv2.FILLED)
        cv2.putText(image, text, (blockTopLeft[0] + int(blockHeight / 4), blockTopLeft[1] + int(blockHeight * 0.667)),
                     cv2.FONT_HERSHEY_COMPLEX_SMALL, fontScale, (0, 0, 0), 1, cv2.LINE_AA)

    def draw_fps(self, image):
        """Helper to draw frame per second onto image"""
        now = time.time()
        if self.frame_count > 0:
            diff = now - self.start
            if diff >= 1:
                self.fps = round(self.frame_count / diff, 1)
                self.frame_count = 0
                self.start = now

        label = "fps " + str(self.fps)
        labelSize, baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        width = image.shape[1]
        height = image.shape[0]
        pos = (width - labelSize[0] - 5, labelSize[1] + 5)
        cv2.putText(image, label, pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (0, 0, 128), 1, cv2.LINE_AA)
        self.frame_count = self.frame_count + 1

    def get_wait(self):
        speed = self.fps
        if (speed == 0):
            speed = 1
        if (speed > 1):
            return 1
        return 3

    def done(self):
        if self.iterations is not None and self.iterations <= 0:
            return True
        # on slow devices this helps let the images to show up on screen
        result = False
        for i in range(self.get_wait()):
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                result = True
                break
            if key == ord(' '):
                self.frame = self.load_next_image()
                
        return result

class TiledImage:
    def __init__(self, numImages=2, outputHeightAndWidth=(600, 800)):
        """ Helper class to create a tiled image out of many smaller images.
        The class calculates how many horizontal and vertical blocks are needed to fit the requested number of images 
        and fills in unused blocks as blank. For example, to fit 4 images, the number of tiles is 2x2, to fit 5 images,
        the number of tiles is 3x2, with the last tile being blank.
        numImages - the maximum number of images that need to be composed into the tiled image. Note that the
                    actual number of tiles is equal to or larger than this number.
        outputHeightAndWidth - a list of two values giving the rows and columns of the output image. The output tiled image 
                            is a composition of sub images.
        """
        self.composed_image_shape = self.get_composed_image_shape(numImages)
        self.number_of_tiles = self.composed_image_shape[0] * self.composed_image_shape[1]
        self.output_height_and_width = outputHeightAndWidth
        self.images = None
        self.window_name = 'ELL side by side'
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL) # Ensure the window is resizable
        # The aspect ratio of the composed image is now self.composed_image_shape[0] : self.composed_image_shape[1]
        # Adjust the height of the window to account for this, else images will look distorted
        cv2.resizeWindow(self.window_name, outputHeightAndWidth[1], int(outputHeightAndWidth[0] * (self.composed_image_shape[0] / self.composed_image_shape[1])))

    def get_composed_image_shape(self, numImages):
        """Returns a tuple indicating the (rows,cols) of the required number of tiles to hold numImages."""
        # Split the image horizontally
        numHorizontal = math.ceil(math.sqrt(numImages))
        # Split the image vertically
        numVertical = math.ceil(numImages / numHorizontal)

        return (numVertical, numHorizontal)

    def compose(self):
        """Composes an image made by tiling all the sub-images set with `set_image_at`. """
        yElements = []
        for verticalIndex in range(self.composed_image_shape[0]):
            xElements = []
            for horizontalIndex in range(self.composed_image_shape[1]):
                currentIndex = verticalIndex * self.composed_image_shape[1] + horizontalIndex
                xElements.append(self.images[currentIndex])
            horizontalImage = np.hstack(tuple(xElements))
            yElements.append(horizontalImage)
        composedImage = np.vstack(tuple(yElements))

        # Draw separation lines
        yStep = int(composedImage.shape[0] / self.composed_image_shape[0])
        xStep = int(composedImage.shape[1] / self.composed_image_shape[1])
        y = yStep
        x = xStep
        for horizontalIndex in range(1, self.composed_image_shape[1]):
            cv2.line(composedImage, (x, 0), (x, composedImage.shape[0]), (0, 0, 0), 3)
            x = x + xStep
        for verticalIndex in range(1, self.composed_image_shape[0]):
            cv2.line(composedImage, (0, y), (composedImage.shape[1], y), (0, 0, 0), 3)
            y = y + yStep
        
        return composedImage

    def set_image_at(self, imageIndex, frame):
        """Sets the image at the specified index. Once all images have been set, the tiled image result can be retrieved with `compose`."""
        # Ensure self.images is initialized.
        if self.images is None:
            self.images = [None] * self.number_of_tiles
            for i in range(self.number_of_tiles):
                self.images[i] = np.zeros((frame.shape), np.uint8)

        # Update the image at the specified index
        if (imageIndex < self.number_of_tiles):
            self.images[imageIndex] = frame
            return True
        return False

    def show(self):
        """Shows the final result of the tiled image. Returns True if the user indicates they are done viewing by pressing `Esc`. """
        # Compose the tiled image
        imageToShow = self.compose()
        # Show the tiled image
        cv2.imshow(self.window_name, imageToShow)
        # Run the update loop and check whether the user has indicated whether they are done
        if cv2.waitKey(1) & 0xFF == 27:
            return True
        return False