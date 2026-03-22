#!/bin/bash

# Script to navigate to the scripts directory and allow user to select which script to run

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/src/robot_arm/rob_bringup/scripts"

# Check if scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "Error: Scripts directory not found at $SCRIPTS_DIR"
    exit 1
fi

# Navigate to scripts directory
cd "$SCRIPTS_DIR"

echo "=========================================="
echo "Robot Arm Script Launcher"
echo "=========================================="
echo "Current directory: $(pwd)"
echo ""

# Robot selection menu
robots=("rob" "panda" "bb01")
echo "Available robots:"
echo ""

# Display available robots with numbers
for i in "${!robots[@]}"; do
    robot_name="${robots[$i]}"
    echo "$((i+1)). $robot_name"
done

echo ""
echo "0. Exit"
echo ""

# Function to get robot selection
get_robot_choice() {
    while true; do
        read -p "Please select a robot (0-${#robots[@]}): " robot_choice
        
        # Check if input is a number
        if [[ "$robot_choice" =~ ^[0-9]+$ ]]; then
            # Check if choice is within valid range
            if [ "$robot_choice" -ge 0 ] && [ "$robot_choice" -le "${#robots[@]}" ]; then
                break
            else
                echo "Invalid choice. Please enter a number between 0 and ${#robots[@]}."
            fi
        else
            echo "Invalid input. Please enter a number."
        fi
    done
}

# Get robot choice
get_robot_choice

# Handle robot choice
if [ "$robot_choice" -eq 0 ]; then
    echo "Exiting..."
    exit 0
fi

# Get the selected robot (convert to 0-based index)
SELECTED_ROBOT="${robots[$((robot_choice-1))]}"

echo ""
echo "Selected robot: $SELECTED_ROBOT"
echo ""

# Find all .sh files in the current directory
all_sh_files=($(ls *.sh 2>/dev/null))

# Filter scripts based on robot selection
# Real robot scripts (real_robot.sh, real_robot_servo.sh) only available for bb01
sh_files=()
for script in "${all_sh_files[@]}"; do
    # Skip real robot scripts if not bb01
    if [[ "$script" =~ ^real_robot ]]; then
        if [ "$SELECTED_ROBOT" = "bb01" ]; then
            sh_files+=("$script")
        fi
        # Skip real robot scripts for non-bb01 robots
    else
        # Include all other scripts for all robots
        sh_files+=("$script")
    fi
done

# Check if any .sh files were found
if [ ${#sh_files[@]} -eq 0 ]; then
    echo "No .sh files found in the scripts directory for robot: $SELECTED_ROBOT"
    exit 1
fi

echo "Available scripts:"
echo ""

# Display available scripts with numbers
for i in "${!sh_files[@]}"; do
    script_name="${sh_files[$i]}"
    # Remove .sh extension for display
    display_name="${script_name%.sh}"
    # Replace underscores with spaces and capitalize
    display_name=$(echo "$display_name" | sed 's/_/ /g' | sed 's/\b\w/\U&/g')
    echo "$((i+1)). $display_name"
done

echo ""
echo "0. Exit"
echo ""

# Function to get user input
get_user_choice() {
    while true; do
        read -p "Please select a script to run (0-${#sh_files[@]}): " choice
        
        # Check if input is a number
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
            # Check if choice is within valid range
            if [ "$choice" -ge 0 ] && [ "$choice" -le "${#sh_files[@]}" ]; then
                break
            else
                echo "Invalid choice. Please enter a number between 0 and ${#sh_files[@]}."
            fi
        else
            echo "Invalid input. Please enter a number."
        fi
    done
}

# Get user choice
get_user_choice

# Handle user choice
if [ "$choice" -eq 0 ]; then
    echo "Exiting..."
    exit 0
fi

# Get the selected script (convert to 0-based index)
selected_script="${sh_files[$((choice-1))]}"

echo ""
echo "Selected script: $selected_script"
echo ""

# Check if the script is executable
if [ ! -x "$selected_script" ]; then
    echo "Making script executable..."
    chmod +x "$selected_script"
fi

# Special handling for scripts that need additional arguments
if [ "$selected_script" = "mtc_demos.sh" ]; then
    echo "This script supports the following execution options:"
    echo "1. alternative_path_costs (default)"
    echo "2. cartesian"
    echo "3. fallbacks_move_to"
    echo "4. ik_clearance_cost"
    echo "5. modular"
    echo ""
    read -p "Enter execution option (or press Enter for default): " exe_option
    
    if [ -z "$exe_option" ]; then
        exe_option="alternative_path_costs"
    fi
    
    echo "Running: ./$selected_script $SELECTED_ROBOT $exe_option"
    echo "=========================================="
    ./"$selected_script" "$SELECTED_ROBOT" "$exe_option"
elif [ "$selected_script" = "real_robot.sh" ]; then
    # Special handling for real robot script (without servo)
    # Only works with bb01
    if [ "$SELECTED_ROBOT" != "bb01" ]; then
        echo "Error: real_robot.sh only works with bb01 robot."
        echo "Selected robot: $SELECTED_ROBOT"
        exit 1
    fi
    
    echo ""
    read -p "Enter serial port (default: /dev/ttyUSB0): " port_input
    PORT=${port_input:-/dev/ttyUSB0}
    
    echo "Running: ./$selected_script $SELECTED_ROBOT $PORT"
    echo "=========================================="
    ./"$selected_script" "$SELECTED_ROBOT" "$PORT"
elif [ "$selected_script" = "real_robot_servo.sh" ]; then
    # Special handling for real robot servo script
    # Only works with bb01
    if [ "$SELECTED_ROBOT" != "bb01" ]; then
        echo "Error: real_robot_servo.sh only works with bb01 robot."
        echo "Selected robot: $SELECTED_ROBOT"
        exit 1
    fi
    
    echo ""
    read -p "Enter serial port (default: /dev/ttyUSB0): " port_input
    PORT=${port_input:-/dev/ttyUSB0}
    
    echo "Running: ./$selected_script $SELECTED_ROBOT $PORT"
    echo "=========================================="
    ./"$selected_script" "$SELECTED_ROBOT" "$PORT"
else
    echo "Running: ./$selected_script $SELECTED_ROBOT"
    echo "=========================================="
    ./"$selected_script" "$SELECTED_ROBOT"
fi

echo ""
echo "Script execution completed."
