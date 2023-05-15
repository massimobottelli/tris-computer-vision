import cv2 as cv
import numpy as np
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Import configuration parameters
FRAME_WIDTH = config['FRAME_WIDTH']
FRAME_HEIGHT = config['FRAME_HEIGHT']
ROTATE = config['ROTATE']
LINE_COLOR = tuple(config['LINE_COLOR'])
CIRCLE_COLOR = tuple(config['CIRCLE_COLOR'])
OVERLAY_COLOR_1 = tuple(config['OVERLAY_COLOR_1'])
OVERLAY_COLOR_2 = tuple(config['OVERLAY_COLOR_2'])
LINE_WEIGHT = config['LINE_WEIGHT']
CELL_WIDTH = int (FRAME_WIDTH / 3)
CELL_HEIGHT = int (FRAME_HEIGHT / 3)
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

    # Rotate the image by 180 degrees
    if ROTATE is True:
        frame = cv.flip(frame, -1)

    return frame


def detect_corners(frame):
    # Detect corners of the rectangle

    # Preprocess image: grayscale, blur and threshold
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.bilateralFilter(gray, 30, 75, 100)
    _, thresh = cv.threshold(blurred, 0, 255, cv.THRESH_OTSU)

    # Find contour
    contours, _ = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contour = contours[0]

    # Approximate contour as a rectangle
    perimeter = cv.arcLength(contour, True)
    approx = cv.approxPolyDP(contour, 0.05 * perimeter, True)

    # Draw rectangle borders
    cv.drawContours(frame, [approx], -1, (0, 0, 255), 2)

    # Store the coordinates of the four corners in an array
    corners = np.zeros((4, 2), dtype=int)
    for i, vertex in enumerate(approx[:4]):
        x, y = vertex[0]
        corners[i] = [x, y]

    return corners


def perspective_trasformation(corners):
    # Perspective trasformation
    pts1 = np.float32([corners])
    pts2 = np.float32([[FRAME_WIDTH, FRAME_HEIGHT], [FRAME_WIDTH, 0], [0, 0], [0, FRAME_HEIGHT]])
    matrix = cv.getPerspectiveTransform(pts1, pts2)
    dst = cv.warpPerspective(frame, matrix, (FRAME_WIDTH, FRAME_HEIGHT))

    return dst


def draw_grid(frame):
    """ Draw reference grid """
    for i, coord in enumerate(cell_coords):
        if i % 2 == 0:
            point1 = coord
            point2 = cell_coords[i + 1]
            cv.line(frame, point1, point2, LINE_COLOR, LINE_WEIGHT, cv.LINE_AA)


def check_cell(img, cell_x, cell_y):
    """Check each cell if not empty"""

    # Extract the region of interest (ROI) of current cell
    cell_roi = img[cell_y:cell_y + CELL_HEIGHT, cell_x:cell_x + CELL_WIDTH]

    # Convert the ROI to grayscale
    cell_gray = cv.cvtColor(cell_roi, cv.COLOR_BGR2GRAY)

    # Threshold the grayscale image to obtain a binary mask
    _, cell_mask = cv.threshold(cell_gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

    # Compute the percentage of the masked area
    mask_percentage = cv.countNonZero(cell_mask) / (CELL_WIDTH * CELL_HEIGHT)

    return cell_mask, mask_percentage


def detect_circle(img, cell_mask):
    """Detect circles"""
    circles = cv.HoughCircles(cell_mask, cv.HOUGH_GRADIENT, dp=1, minDist=MINDIST, param1=PARAM1,
                              param2=PARAM2, minRadius=MINRADIUS, maxRadius=MAXRADIUS)

    # Draw detected circles on original image
    circleDetected = False

    if circles is not None:
        circleDetected = True
        circles = np.round(circles[0, :]).astype("int")
        for (origin_x, origin_y, radius) in circles:
            cv.circle(img, (cell_x + origin_x, cell_y + origin_y), radius, LINE_COLOR, LINE_WEIGHT)

    return circleDetected


def fill_overlay(img, symbol):
    """Fill the cell with overlay"""

    color = OVERLAY_COLOR_1 if symbol == 1 else OVERLAY_COLOR_2

    overlay = img.copy()
    cv.rectangle(overlay, (cell_x, cell_y), (cell_x + CELL_WIDTH, cell_y + CELL_HEIGHT), color, -1)
    alpha = 0.3
    cv.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


''' Main code '''

# Create list to store cells coordinates
cell_coords = create_coords()

# Initialize the video capture object
cap = cv.VideoCapture(0)


# Main loop
while True:

    # Empty board
    board_symbol = [["", "", ""] for i in range(3)]

    # Get frame from webcam
    frame = get_frame()

    # Detect corners
    corners = detect_corners(frame)

    # Adjust perspective
    board = perspective_trasformation(corners)

    # Draw reference grid
    draw_grid(board)

    # Check each cell if not empty
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):

            # Get the coordinates of the current cell
            cell_x = MARGIN_X + j * CELL_WIDTH
            cell_y = MARGIN_Y + i * CELL_HEIGHT

            # calculate mask percentage
            cell_mask, mask_percentage = check_cell(board, cell_x, cell_y)

            # if cell is not empty, detect circle and show overlay
            if mask_percentage > EMPTY_THRESHOLD:

                # Detect circles
                circleDetected = detect_circle(board, cell_mask)


                if circleDetected is True:

                    # add O symbol to the board
                    board_symbol[i][j] = "O"

                    # Fill the cell with overlay color 1
                    fill_overlay(board, 1)

                else:
                    # add X symbol to the board
                    board_symbol[i][j] = "X"

                    # Fill the cell with overlay color 2
                    fill_overlay(board, 2)

            else:
                # if empty is cell
                board_symbol [i][j] = " "

    # Print the board to the console
    for row in board_symbol:
        for element in row:
            print(element, end=' ')
        print()
    print("------")

    # Display the windows

    # Create a blank canvas to combine the images
    canvas = np.zeros((FRAME_HEIGHT * 2, FRAME_WIDTH, 3), dtype=np.uint8)
    canvas[:FRAME_HEIGHT, :] = frame
    canvas[FRAME_HEIGHT:, :] = board
    cv.imshow("Board", canvas)

    # Display the windows
    # cv.imshow("Webcam", frame)
    # cv.imshow("Board", board)

    # get the key pressed to loop
    if cv.waitKey(0) == 27:
        break

# Release the video capture object and close the window
cap.release()
cv.destroyAllWindows()
