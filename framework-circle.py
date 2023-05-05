# display 3x3 framework to align webcam
# and detects circles in each frame

import cv2 as cv
import numpy as np
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Import configuration parameters
FRAME_HEIGHT = config['FRAME_HEIGHT']
FRAME_WIDTH = config['FRAME_WIDTH']
LINE_COLOR = tuple(config['LINE_COLOR']) # Convert to tuple
CIRCLE_COLOR = tuple(config['CIRCLE_COLOR']) # Convert to tuple
OVERLAY_COLOR_1 = tuple(config['OVERLAY_COLOR_1']) # Convert to tuple
OVERLAY_COLOR_2 = tuple(config['OVERLAY_COLOR_2']) # Convert to tuple
LINE_WEIGHT = config['LINE_WEIGHT']
CELL_WIDTH = config['CELL_WIDTH']
CELL_HEIGHT = config['CELL_HEIGHT']
MARGIN_X = config['MARGIN_X']
MARGIN_Y = config['MARGIN_Y']
NUM_ROWS = config['NUM_ROWS']
NUM_COLS = config['NUM_COLS']
EMPTY_THRESHOLD = config['EMPTY_THRESHOLD']
MINDIST = config['MINDIST']
PARAM1 = config['PARAM1']
PARAM2 = config['PARAM2']
MINRADIUS = config['MINRADIUS']
MAXRADIUS = config['MAXRADIUS']


def create_coords():
    """Create list to store cells coordinates"""
    cell_coords = []
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS + 1):
            # calculate x and y coordinates of the top-left corner of the cell
            x = MARGIN_X + j * CELL_WIDTH
            y = MARGIN_Y + i * CELL_HEIGHT
            # add coordinates of the top and bottom of the cell
            cell_coords.append((x, y))
            cell_coords.append((x, y + CELL_HEIGHT))
        # add coordinates of the left and right edges of the row
        cell_coords.append((MARGIN_X, MARGIN_Y + i * CELL_HEIGHT))
        cell_coords.append((MARGIN_X + NUM_COLS * CELL_WIDTH, MARGIN_Y + i * CELL_HEIGHT))
    # Add coordinates of the bottom edge of the grid
    cell_coords.append((MARGIN_X, MARGIN_Y + NUM_ROWS * CELL_HEIGHT))
    cell_coords.append((MARGIN_X + NUM_COLS * CELL_WIDTH, MARGIN_Y + NUM_ROWS * CELL_HEIGHT))
    return cell_coords

def get_frame():
    """ Get frame from webcam and process it """

    # Read a frame from the video capture object
    ret, frame = cap.read()

    # Crop the frame to a square
    height, width = frame.shape[:2]
    size = min(height, width)
    x = (width - size) // 2
    y = (height - size) // 2
    frame = frame[y:y+size, x:x+size]

    # Resize the image
    frame = cv.resize(frame, (FRAME_HEIGHT, FRAME_WIDTH))

    # Flip the image horizontally and vertically
    frame = cv.flip(frame, -1)

    return frame

def draw_grid():
    """ Draw reference grid """
    for i, coord in enumerate(cell_coords):
        if i % 2 == 0:
            point1 = coord
            point2 = cell_coords[i + 1]
            cv.line(frame, point1, point2, LINE_COLOR, LINE_WEIGHT, cv.LINE_AA)


def check_cell():
    """Check each cell if not empty"""

    # Extract the region of interest (ROI) of current cell
    cell_roi = frame[cell_y:cell_y + CELL_HEIGHT, cell_x:cell_x + CELL_WIDTH]

    # Convert the ROI to grayscale
    cell_gray = cv.cvtColor(cell_roi, cv.COLOR_BGR2GRAY)

    # Threshold the grayscale image to obtain a binary mask
    _, cell_mask = cv.threshold(cell_gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

    # Compute the percentage of the masked area
    mask_percentage = cv.countNonZero(cell_mask) / (CELL_WIDTH * CELL_HEIGHT)

    return cell_mask, mask_percentage


def detect_circle(cell_mask):
    """Detect circles"""
    circles = cv.HoughCircles(cell_mask, cv.HOUGH_GRADIENT, dp=1, minDist=MINDIST, param1=PARAM1,
                              param2=PARAM2, minRadius=MINRADIUS, maxRadius=MAXRADIUS)

    # Draw detected circles on original image
    circleDetected = False

    if circles is not None:
        circleDetected = True
        circles = np.round(circles[0, :]).astype("int")
        for (origin_x, origin_y, radius) in circles:
            cv.circle(frame, (cell_x + origin_x, cell_y + origin_y), radius, LINE_COLOR, LINE_WEIGHT)

    return circleDetected


def fill_overlay(player):
    """Fill the cell with overlay"""

    color = OVERLAY_COLOR_1 if player == 1 else OVERLAY_COLOR_2

    overlay = frame.copy()
    cv.rectangle(overlay, (cell_x, cell_y), (cell_x + CELL_WIDTH, cell_y + CELL_HEIGHT), color, -1)
    alpha = 0.3
    cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


''' Main code '''

cell_coords = create_coords()
# Create list to store cells coordinates

# Initialize the video capture object
cap = cv.VideoCapture(0)

# First loop: show video in real-time until space key is pressed
while True:
    # Get frame from webcam
    frame = get_frame()

    # Draw reference grid
    draw_grid()

    # Check each cell if not empty
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):

            # Get the coordinates of the current cell
            cell_x = MARGIN_X + j * CELL_WIDTH
            cell_y = MARGIN_Y + i * CELL_HEIGHT

            # check if cell is empty
            cell_mask, mask_percentage = check_cell()
            if mask_percentage > EMPTY_THRESHOLD:
                fill_overlay(2)

    # Display the frame
    cv.imshow("Align board to reference grid", frame)

    # Wait for space bar press
    if cv.waitKey(1) == ord(' '):
        break

# Second loop: wait for space key press to capture image and show, press 'q' key to exit
while True:

    # get the key pressed
    key = cv.waitKey(0)

    # check if space key is pressed
    if key == ord(' '):

        # Get frame from webcam
        frame = get_frame()

        # Draw reference grid
        draw_grid()

        # Check each cell if not empty
        for i in range(NUM_ROWS):
            for j in range(NUM_COLS):

                # Get the coordinates of the current cell
                cell_x = MARGIN_X + j * CELL_WIDTH
                cell_y = MARGIN_Y + i * CELL_HEIGHT

                # check if cell is empty
                cell_mask, mask_percentage = check_cell()
                if mask_percentage > EMPTY_THRESHOLD:
                    # Detect circles
                    circleDetected = detect_circle(cell_mask)

                    player = 1 if circleDetected == True else 2
                    # Fill the cell with overlay
                    fill_overlay(player)

        # Display the frame
        cv.imshow("Detected image", frame)

    if key == 27:
        # ESC to quit
        break

# Release the video capture object and close the window
cap.release()
cv.destroyAllWindows()

