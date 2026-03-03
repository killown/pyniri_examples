import subprocess
from pyniri import NiriSocket


def turn_off_output(output_name="DP-1"):
    """
    Turn off the specified output using niri msg.
    """
    try:
        subprocess.run(["niri", "msg", "output", output_name, "off"], check=True)
        print(f"Turned off {output_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to turn off {output_name}: {e}")


def turn_on_output(output_name="DP-1"):
    """
    Turn on the specified output using niri msg.
    """
    try:
        subprocess.run(["niri", "msg", "output", output_name, "on"], check=True)
        print(f"Turned on {output_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to turn on {output_name}: {e}")


def get_output_state(niri, output_name="DP-1"):
    """
    Get the current state of the output (on or off).
    In Niri, an output is 'off' if its logical configuration is None.
    """
    outputs = niri.get_outputs()
    if output_name not in outputs:
        return "unknown"

    # logical is None when the output is disabled
    return "on" if outputs[output_name].get("logical") else "off"


def toggle_output(niri, output_name="DP-1"):
    """
    Toggle the output state (off if on, on if off).
    """
    current_state = get_output_state(niri, output_name)
    if current_state == "off":
        turn_on_output(output_name)
    else:
        turn_off_output(output_name)


if __name__ == "__main__":
    # Initialize the NiriSocket
    niri = NiriSocket()

    # Toggle the output state
    toggle_output(niri, output_name="DP-1")
