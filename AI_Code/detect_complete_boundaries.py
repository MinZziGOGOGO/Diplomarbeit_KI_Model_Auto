import cv2
import numpy as np

# Function to do nothing (required for creating trackbars)
def nothing(x):
    pass

# Initialize the video capture object for the laptop camera
cap = cv2.VideoCapture(0)

# Create a named window to attach the trackbars
cv2.namedWindow('Settings')

# Create trackbars for adjusting Canny thresholds
cv2.createTrackbar('Low Threshold', 'Settings', 50, 255, nothing)
cv2.createTrackbar('High Threshold', 'Settings', 150, 255, nothing)

# Create a trackbar for adjusting the dilation kernel size
cv2.createTrackbar('Dilation Kernel', 'Settings', 1, 10, nothing)

# Create a trackbar for adjusting the contour approximation factor (epsilon), starting at 0
cv2.createTrackbar('Contour Approx (x0.01)', 'Settings', 0, 20, nothing)

# Create trackbars for controlling the fade-out and contribution rates
cv2.createTrackbar('Fade-out (Old Mask)', 'Settings', 70, 100, nothing)  # Starts at 0.7 (70%)
cv2.createTrackbar('New Mask Contribution', 'Settings', 30, 100, nothing)  # Starts at 0.3 (30%)

# Create an empty accumulator mask to store previous filled contours
accumulated_mask = None

while True:
    # Capture frame-by-frame from the camera
    ret, frame = cap.read()

    # If frame is not captured properly, break the loop
    if not ret:
        break

    # Display the original input video feed
    cv2.imshow("Original Video Feed", frame)

    # Get current positions of the sliders
    low_threshold = cv2.getTrackbarPos('Low Threshold', 'Settings')
    high_threshold = cv2.getTrackbarPos('High Threshold', 'Settings')
    dilation_kernel = cv2.getTrackbarPos('Dilation Kernel', 'Settings')
    epsilon_factor = cv2.getTrackbarPos('Contour Approx (x0.01)', 'Settings') / 100.0

    # Get fade-out and contribution values (from percentage to fractions)
    fade_out_rate = cv2.getTrackbarPos('Fade-out (Old Mask)', 'Settings') / 100.0
    new_mask_contribution = cv2.getTrackbarPos('New Mask Contribution', 'Settings') / 100.0

    # Ensure fade-out + contribution rates don't exceed 1 (normalize if needed)
    if fade_out_rate + new_mask_contribution > 1:
        total = fade_out_rate + new_mask_contribution
        fade_out_rate /= total
        new_mask_contribution /= total

    # Convert the frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding to handle different object intensities
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # Use dilation to close small gaps in contours (using dynamic kernel size)
    kernel = np.ones((dilation_kernel, dilation_kernel), np.uint8)
    dilated_edges = cv2.dilate(adaptive_thresh, kernel, iterations=1)

    # Find contours based on the dilated adaptive threshold
    contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Create a mask with the same dimensions as the frame (initialized to black)
    mask = np.zeros(frame.shape[:2], dtype="uint8")

    # Create a copy of the original frame to draw the contours before filling
    contour_frame = frame.copy()

    # Draw the contours on the copy of the frame (before filling them)
    cv2.drawContours(contour_frame, contours, -1, (0, 255, 0), 2)

    # Draw and fill only closed or nearly closed contours
    for contour in contours:
        # Approximate the contour to reduce noise and smooth it (using dynamic epsilon)
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour is sufficiently large to avoid noise
        if cv2.contourArea(approx) > 500:
            # Only fill the contour if it's closed
            is_closed = cv2.isContourConvex(approx) or len(approx) > 4
            if is_closed:
                # Fill the contour if it's closed or nearly closed
                cv2.drawContours(mask, [approx], -1, (255, 255, 255), thickness=cv2.FILLED)

    # Initialize the accumulated mask the first time
    if accumulated_mask is None:
        accumulated_mask = mask.copy().astype("uint8")
    else:
        # Apply the user-defined fade-out and contribution rates dynamically
        accumulated_mask = cv2.addWeighted(accumulated_mask, fade_out_rate, mask, new_mask_contribution, 0)

    # ---- Smoothing the Filled Areas ----
    # Apply morphological opening to smooth the filled-in areas
    smoothing_kernel = np.ones((5, 5), np.uint8)  # You can adjust the size of the kernel to smooth more
    smoothed_mask = cv2.morphologyEx(accumulated_mask, cv2.MORPH_OPEN, smoothing_kernel)

    # Create the red background for the filled contours
    red_background = np.zeros_like(frame)
    red_background[:, :] = (0, 0, 255)  # Fill the background with red color

    # Apply the smoothed mask to the red background instead of the original frame
    result = cv2.bitwise_and(red_background, red_background, mask=smoothed_mask)

    # ---- Draw Bounding Boxes Around Each Red Object ----
    for contour in contours:
        if cv2.contourArea(contour) > 500:
            # Calculate the bounding box around each contour
            x, y, w, h = cv2.boundingRect(contour)
            # Draw the bounding box in green on the result
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green bounding box

    # Display only the flipped red-filled areas with bounding boxes
    cv2.imshow("Segmented Object with Red Filled Contours and Bounding Boxes", result)

    # Press 'q' to exit the loop and close the window
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
