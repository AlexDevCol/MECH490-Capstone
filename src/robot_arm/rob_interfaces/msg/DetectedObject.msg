# Represents a single detected object (either pick or place)

# Type constants
uint8 TYPE_UNKNOWN = 0
uint8 TYPE_PICK = 1
uint8 TYPE_PLACE = 2

# Object type: Use constants defined above
uint8 type

# --- Fields relevant for PICK objects ---
# Radius of the collision sphere for a pick object
float64 pick_radius

# --- Fields relevant for PLACE locations ---
# Grid coordinates for a place location (optional, use -1 if not applicable)
int32 place_row
int32 place_col

# --- Fields relevant for BOTH (interpreted based on type) ---
# Center coordinates (e.g., in pixels from Gemini, or later in meters in world frame)
# It's highly recommended to convert these to meters in a known frame_id
# before publishing, or handle the conversion in the subscriber.
float64 center_x
float64 center_y
# Consider adding center_z if you have depth information
# float64 center_z