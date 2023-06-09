import cv2 as cv
import numpy as np
import yaml
import random

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Import configuration parameters
FRAME_WIDTH = config['FRAME_WIDTH']
FRAME_HEIGHT = config['FRAME_HEIGHT']
NUM_ROWS = config['NUM_ROWS']
NUM_COLS = config['NUM_COLS']

CELL_WIDTH = int (FRAME_WIDTH / 3)
CELL_HEIGHT = int (FRAME_HEIGHT / 3)

CIRCLE_COLOR = tuple(config['CIRCLE_COLOR'])
OVERLAY_COLOR_1 = tuple(config['OVERLAY_COLOR_1'])
OVERLAY_COLOR_2 = tuple(config['OVERLAY_COLOR_2'])
OVERLAY_COLOR_3 = tuple(config['OVERLAY_COLOR_3'])
LINE_COLOR = tuple(config['LINE_COLOR'])
LINE_WEIGHT = config['LINE_WEIGHT']

EMPTY_THRESHOLD = config['EMPTY_THRESHOLD']
MINDIST = config['MINDIST']
PARAM1 = config['PARAM1']
PARAM2 = config['PARAM2']
MINRADIUS = config['MINRADIUS']
MAXRADIUS = config['MAXRADIUS']

HUMAN_PLAYER = config['HUMAN_PLAYER']
COMPUTER_PLAYER = config['COMPUTER_PLAYER']

def create_coords():
    """Create list to store cells coordinates"""
    cell_coords = []
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS + 1):
            # calculate x and y coordinates of the top-left corner of the cell
            x = j * CELL_WIDTH
            y = i * CELL_HEIGHT
            # add coordinates of the top and bottom of the cell
            cell_coords.append((x, y))
            cell_coords.append((x, y + CELL_HEIGHT))
        # add coordinates of the left and right edges of the row
        cell_coords.append((0, i * CELL_HEIGHT))
        cell_coords.append((NUM_COLS * CELL_WIDTH, i * CELL_HEIGHT))
    # Add coordinates of the bottom edge of the grid
    cell_coords.append((0, NUM_ROWS * CELL_HEIGHT))
    cell_coords.append((NUM_COLS * CELL_WIDTH, NUM_ROWS * CELL_HEIGHT))
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


def check_cell(img, j, i):
    """Check each cell if not empty"""
    cell_x = j * CELL_WIDTH
    cell_y = i * CELL_HEIGHT

    # Extract the region of interest (ROI) of current cell
    cell_roi = img[cell_y:cell_y + CELL_HEIGHT, cell_x:cell_x + CELL_WIDTH]

    # Convert the ROI to grayscale
    cell_gray = cv.cvtColor(cell_roi, cv.COLOR_BGR2GRAY)

    # Threshold the grayscale image to obtain a binary mask
    _, cell_mask = cv.threshold(cell_gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

    # Compute the percentage of the masked area
    mask_percentage = cv.countNonZero(cell_mask) / (CELL_WIDTH * CELL_HEIGHT)

    return cell_mask, mask_percentage


def detect_circle(img, j, i, cell_mask):
    """Detect circles"""

    cell_x = j * CELL_WIDTH
    cell_y = i * CELL_HEIGHT

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


def fill_overlay(img, j, i, symbol):
    """Fill the cell with overlay"""

    cell_x = j * CELL_WIDTH
    cell_y = i * CELL_HEIGHT

    if symbol == 1:
        color = OVERLAY_COLOR_1

    if symbol == 2:
        color = OVERLAY_COLOR_2

    if symbol == 3:
        color = OVERLAY_COLOR_3

    alpha = 0.4
    overlay = img.copy()
    cv.rectangle(overlay, (cell_x, cell_y), (cell_x + CELL_WIDTH, cell_y + CELL_HEIGHT), color, -1)
    cv.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def computer_move(board):

    # Find winning move
    move = find_winning_move(board, COMPUTER_PLAYER)

    if move is None:
        # Find blocking move
        move = find_winning_move(board, HUMAN_PLAYER)

    if move is None:
        while True:
            i = random.randint(0, NUM_ROWS - 1)
            j = random.randint(0, NUM_COLS - 1)
            move = [i,j]
            if board[i][j] == 1:
                break

    return move


def find_winning_move(values, player):
    check = player ** 2
    row_product = [1] * 3
    col_product = [1] * 3
    diagonal1_product = 1
    diagonal2_product = 1

    for i in range(3):
        for j in range(3):
            row_product[i] *= values[i][j]
            col_product[j] *= values[i][j]
            if i == j:
                diagonal1_product *= values[i][j]
            if i + j == 2:
                diagonal2_product *= values[i][j]

    if check in row_product:
        row = row_product.index(check)
        for col in range(3):
            if values[row][col] == 1:
                return (row, col)
    elif check in col_product:
        col = col_product.index(check)
        for row in range(3):
            if values[row][col] == 1:
                return (row, col)
    elif diagonal1_product == check:
        for i in range(3):
            if values[i][i] == 1:
                return (i, i)
    elif diagonal2_product == check:
        for i in range(3):
            if values[i][2-i] == 1:
                return (i, 2-i)
    else:
        return None


def check_winner(board):
    winners = []
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] and board[i][0] != 1:
            return ([i, 0], [i, 1], [i, 2])

        if board[0][i] == board[1][i] == board[2][i] and board[0][i] != 1:
            return ([0, i], [1, i], [2, i])

    if board[0][0] == board[1][1] == board[2][2] and board[0][0] != 1:
        return ([0, 0], [1, 1], [2, 2])

    if board[0][2] == board[1][1] == board[2][0] and board[0][2] != 1:
        return ([0, 2], [1, 1], [2, 0])

    return None

''' Main '''

turn = HUMAN_PLAYER

# Create list to store cells coordinates
cell_coords = create_coords()

# Initialize the video capture object
cap = cv.VideoCapture(0)

# Main loop
while True:

    # Get frame from webcam
    frame = get_frame()

    # Detect corners
    corners = detect_corners(frame)

    # Adjust perspective
    board = perspective_trasformation(corners)

    # Draw reference grid
    draw_grid(board)

    # Empty numeric board
    numeric_board = [[1, 1, 1] for i in range(NUM_ROWS)]

    # Check each cell
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):

            # calculate mask percentage
            cell_mask, mask_percentage = check_cell(board, j, i)

            # if cell is not empty, detect circle and show overlay
            if mask_percentage > EMPTY_THRESHOLD:

                # Detect circles
                circleDetected = detect_circle(board, j, i, cell_mask)

                if circleDetected is True:

                    # add HUMAN PLAYER value to numeric board
                    numeric_board[i][j] = HUMAN_PLAYER

                    # Fill the cell with overlay color 1
                    fill_overlay(board, j, i, 1)

                else:
                    # add COMPUTER PLAYER value to numeric board
                    numeric_board[i][j] = COMPUTER_PLAYER

                    # Fill the cell with overlay color 2
                    fill_overlay(board, j, i, 2)

    # Print the board to the console
    for row in numeric_board:
        for element in row:
            print(element, end=' ')
        print()
    print("------")

    # Check if there is a winner
    winning_cells = check_winner(numeric_board)
    if winning_cells is not None:

        print (winning_cells)
        i,j = winning_cells[0]
        if numeric_board[i][j] == HUMAN_PLAYER:
            print ("You win!")
        else:
            print ("Computer wins!")

        # Highlight winning cells
        for coord in winning_cells:
            x, y = coord
            fill_overlay(board, y, x, 3)

    else:

        if turn == COMPUTER_PLAYER:
            # Computer move
            best_move = computer_move(numeric_board)
            print (best_move)

            # Draw X in best move cell
            center_x = (best_move[1] * CELL_WIDTH) + (CELL_WIDTH // 2)
            center_y = (best_move[0] * CELL_HEIGHT) + (CELL_HEIGHT // 2)
            cv.line(board, (center_x - 40, center_y - 40), (center_x + 40, center_y + 40), LINE_COLOR, LINE_WEIGHT * 2)
            cv.line(board, (center_x + 40, center_y - 40), (center_x - 40, center_y + 40), LINE_COLOR, LINE_WEIGHT * 2)

    turn = COMPUTER_PLAYER if turn == HUMAN_PLAYER else HUMAN_PLAYER
    # Display the windows

    # Create a blank canvas to combine the images
    canvas = np.zeros((FRAME_HEIGHT * 2, FRAME_WIDTH, 3), dtype=np.uint8)
    canvas[:FRAME_HEIGHT, :] = frame
    canvas[FRAME_HEIGHT:, :] = board
    cv.imshow("Board", canvas)

    # get the key pressed to loop
    if cv.waitKey(0) == 27:
        break

# Release the video capture object and close the window
cap.release()
cv.destroyAllWindows()
