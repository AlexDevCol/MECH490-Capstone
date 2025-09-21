# List of detected objects from the perception system (e.g., Gemini API)

# Header for timestamp and frame_id information.
# VERY IMPORTANT: The frame_id should eventually be the TF frame
# in which the center_x, center_y coordinates are expressed (e.g., "camera_link" or "world").
std_msgs/Header header

# Array of detected objects
moveo_interfaces/DetectedObject[] objects