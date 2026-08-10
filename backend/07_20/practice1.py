from source import get_camera_position, CameraPosition
from pprint import pprint


def main():
    data:list[CameraPosition] = get_camera_position()
    pprint(data)

if __name__ == "__main__":
    main()