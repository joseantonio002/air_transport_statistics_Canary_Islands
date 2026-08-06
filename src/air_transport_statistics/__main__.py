print(f"Executing {__file__}")
from sys import path, modules
print(path)
print(modules)
print(dir())
from air_transport_statistics.app import main


if __name__ == "__main__":
    raise SystemExit(main())
