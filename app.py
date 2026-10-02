import argparse
from degree_path import create_app

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port, debug=False)
